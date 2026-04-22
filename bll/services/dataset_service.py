import os
import pandas as pd
import uuid
from typing import Sequence
from dal.repositories import DatasetRepository
from dal import Dataset
from dotenv import load_dotenv

load_dotenv()

class DatasetService:
    def __init__(self, dataset_repo: DatasetRepository):
        self.dataset_repo = dataset_repo
        self.storage_dir = os.getenv("STORAGE_DIR")
        os.makedirs(self.storage_dir, exist_ok=True)

    def upload_dataset(self, user_id: int, file_bytes: bytes, filename: str) -> Dataset:
        ext = filename.split('.')[-1].lower()
        if ext not in ['csv', 'xlsx', 'xls']:
            raise ValueError("Поддерживаются только форматы CSV и Excel.")
        
        user_dir = os.path.join(self.storage_dir, f"user_{user_id}")
        os.makedirs(user_dir, exist_ok=True)

        unique_filename = f"{uuid.uuid4().hex[:8]}_{filename}"
        file_path = os.path.join(user_dir, unique_filename)

        with open(file_path, "wb") as f:
            f.write(file_bytes)

        try:
            if ext == 'csv':
                pd.read_csv(file_path, nrows=5, sep=None, engine='python')
            else:
                pd.read_excel(file_path, nrows=5)
        except Exception as ex:
            os.remove(file_path)
            raise ValueError(f"Ошибка чтения файла. Возможно, он поврежден или имеет неверную кодировку: {ex}")
        
        return self.dataset_repo.create(
            user_id=user_id, 
            file_path=file_path,
            file_name=filename
        )
    
    def get_user_datasets(self, user_id: int) -> Sequence[Dataset]:
        return self.dataset_repo.get_all_by_user(user_id)
    
    def get_dataframe(self, dataset_id: int) -> pd.DataFrame:
        dataset = self.dataset_repo.get_by_id(dataset_id)
        if not dataset:
            raise ValueError("Датасет не найден в базе данных.")
        
        if not os.path.exists(dataset.file_path):
            raise FileNotFoundError("Физический файл был удалён с сервера.")
        
        ext = dataset.file_name.split('.')[-1].lower()
        if ext == 'csv':
            return pd.read_csv(dataset.file_path, sep=None, engine='python')
        else:
            return pd.read_excel(dataset.file_path)
        
    def delete_dataset(self, dataset_id: int):
        dataset = self.dataset_repo.get_by_id(dataset_id)
        if dataset:
            if os.path.exists(dataset.file_path):
                os.remove(dataset.file_path)
            self.dataset_repo.delete(dataset_id)