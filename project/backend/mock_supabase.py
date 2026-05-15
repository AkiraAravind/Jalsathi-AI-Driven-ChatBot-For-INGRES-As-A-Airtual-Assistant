"""Mock Supabase client for development/testing without a real database"""
from datetime import datetime
from typing import Any, Dict, List, Optional

class MockTable:
    def __init__(self, data: Dict[str, List[Dict[str, Any]]]):
        self.data = data
        self.filters = []
        self.eq_filters = {}
        self.limit_count = None
        self.select_fields = None
        self.order_field = None
        self.order_desc = False
        self.pending_insert_data = None
        self.pending_update_data = None
        
    def select(self, *fields, count=None):
        if fields:
            self.select_fields = fields
        return self
    
    def eq(self, field: str, value: Any):
        self.eq_filters[field] = value
        return self
    
    def limit(self, count: int):
        self.limit_count = count
        return self
    
    def order(self, field: str, desc=False):
        self.order_field = field
        self.order_desc = desc
        return self
    
    def execute(self):
        # Resolve table data from the selected table context.
        table_name = getattr(self, "table_name", None)
        if table_name and table_name in self.data:
            table_data = self.data[table_name]
        elif self.data:
            table_data = next(iter(self.data.values()))
        else:
            table_data = []
        
        # Handle insert query
        if self.pending_insert_data is not None:
            row = dict(self.pending_insert_data)
            if "created_at" not in row:
                row["created_at"] = datetime.now().isoformat()
            table_data.append(row)
            self.pending_insert_data = None
            return MockResponse(data=[row], count=1)

        # Apply filters
        filtered = table_data
        for field, value in self.eq_filters.items():
            filtered = [row for row in filtered if row.get(field) == value]

        # Handle update query
        if self.pending_update_data is not None:
            updated_rows = []
            for row in filtered:
                row.update(self.pending_update_data)
                updated_rows.append(row)
            self.pending_update_data = None
            return MockResponse(data=updated_rows, count=len(updated_rows))

        # Apply ordering
        if self.order_field:
            filtered = sorted(filtered, key=lambda r: r.get(self.order_field), reverse=self.order_desc)

        # Apply limit
        if self.limit_count:
            filtered = filtered[:self.limit_count]

        # Return mock select response
        return MockResponse(data=filtered, count=len(filtered))
    
    def insert(self, data: Dict[str, Any]):
        self.pending_insert_data = data
        return self
    
    def update(self, data: Dict[str, Any]):
        self.pending_update_data = data
        return self


class MockResponse:
    def __init__(self, data: List[Dict[str, Any]], count: int = None):
        self.data = data
        self.count = count if count is not None else len(data)


class MockInsertResponse:
    def __init__(self, data: Dict[str, Any]):
        self.data = [data]


class MockUpdateResponse:
    def __init__(self):
        self.data = []


class MockSupabaseClient:
    def __init__(self):
        # In-memory storage
        self.tables = {
            "users": [],
            "chat_history": [],
            "groundwater_time_series": [],
        }
    
    def table(self, table_name: str) -> MockTable:
        data = self.tables.get(table_name, [])
        mock_table = MockTable({table_name: data})
        mock_table.table_name = table_name
        return mock_table


def create_mock_client():
    """Factory function to create a mock Supabase client"""
    return MockSupabaseClient()
