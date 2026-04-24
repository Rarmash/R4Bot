from __future__ import annotations

from modules import firebase as firebase_module


class FirebaseService:
    def create_record(self, server_id, database, child: str, payload):
        firebase_module.create_record(server_id, database, child, payload)

    def update_record(self, server_id, database, child: str, payload):
        firebase_module.update_record(server_id, database, child, payload)

    def get_from_record(self, server_id, database, child: str):
        return firebase_module.get_from_record(server_id, database, child)

    def get_all_records(self, server_id, database):
        return firebase_module.get_all_records(server_id, database)

    def search_record(self, server_id, database, child: str, query):
        return firebase_module.search_record(server_id, database, child, query)

    def search_record_id(self, server_id, database, child: str, query):
        return firebase_module.search_record_id(server_id, database, child, query)

    def delete_record(self, server_id, database, child: str):
        firebase_module.delete_record(server_id, database, child)

    def filter_records_by_quantity(self, server_id, database, child: str, quantity):
        return firebase_module.filter_records_by_quantity(server_id, database, child, quantity)
