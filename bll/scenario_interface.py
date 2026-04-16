from abc import ABC, abstractmethod
import pandas as pd
from typing import Dict, Any

class ScenarioInterface(ABC):
    def __init__(self, df: pd.DataFrame, config: Dict[str, Any]):
        self.df = df.copy()
        self.config = config
        self.results = {}

    @abstractmethod
    def validate_config(self) -> bool:
        pass

    @abstractmethod
    def preprocess(self):
        pass

    @abstractmethod
    def execute(self):
        pass

    @abstractmethod
    def get_results(self):
        return self.results