from typing import Optional, Sequence
from sqlalchemy import select, update, delete
from sqlalchemy.orm import Session
from dal.models import Dataset

class DatasetRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, user_id: int, file_path: str, file_name: str) -> Dataset:
        dataset = Dataset(
            user_id=user_id,
            file_path=file_path,
            file_name=file_name
        )
        self.session.add(dataset)
        self.session.flush()
        return dataset

    def get_by_id(self, dataset_id: int) -> Optional[Dataset]:
        return self.session.get(Dataset, dataset_id)

    def get_all_by_user(self, user_id: int) -> Sequence[Dataset]:
        stmt = select(Dataset).where(Dataset.user_id == user_id)
        return self.session.execute(stmt).scalars().all()

    def update(self, dataset_id: int, **values) -> None:
        if not values:
            return
        stmt = update(Dataset).where(Dataset.dataset_id == dataset_id).values(**values)
        self.session.execute(stmt)

    def delete(self, dataset_id: int) -> None:
        stmt = delete(Dataset).where(Dataset.dataset_id == dataset_id)
        self.session.execute(stmt)