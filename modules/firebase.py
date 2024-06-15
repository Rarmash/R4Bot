import json

from firebase_admin import credentials, initialize_app, db, storage, App


def create_firebase_app(databaseID: str):
    cred_obj = credentials.Certificate("firebaseConfig.json")
    firebase = initialize_app(cred_obj,
                              {"databaseURL": f"https://{databaseID}-default-rtdb.firebaseio.com/"})
    return firebase


def create_storage_app(storageID: str):
    cred_obj = credentials.Certificate("firebaseConfig.json")
    storage = initialize_app(cred_obj,
                             {"storageBucket": f"{storageID}.appspot.com"},
                             name="Storage Database")
    return storage


def create_record(server_id, database, child: str, json_set):
    ref = db.reference(f"{server_id}/{database}")
    record_ref = ref.child(child)
    record_ref.set(json_set)


def update_record(server_id, database, child: str, json_set):
    ref = db.reference(f"{server_id}/{database}")
    record_ref = ref.child(child)
    record_ref.update(json_set)


def get_from_record(server_id, database, child: str):
    ref = db.reference(f"{server_id}/{database}")
    record_ref = ref.child(child)
    record = record_ref.get()
    return record


def get_all_records(server_id, database):
    ref = db.reference(f"{server_id}/{database}")
    records = ref.get()
    return records


def search_record(server_id, database, child: str, query):
    ref = db.reference(f"{server_id}/{database}")
    record_ref = ref.order_by_child(child).equal_to(query)
    record = record_ref.get()
    record = json.dumps(next(iter(record.values())))
    return record


def search_record_id(server_id, database, child: str, query):
    ref = db.reference(f"{server_id}/{database}")
    record_ref = ref.order_by_child(child).equal_to(query)
    record = record_ref.get()
    record_id = list(record.keys())[0]
    return record_id


def delete_record(server_id, database, child: str):
    ref = db.reference(f"{server_id}/{database}")
    record_ref = ref.child(child)
    record_ref.delete()


def filter_records_by_quantity(server_id, database, child: str, quantity):
    ref = db.reference(f"{server_id}/{database}")
    records_ref = ref.order_by_child(child).start_at(quantity)
    records = records_ref.get()
    records = json.dumps(records)
    return records


def get_file_from_storage(filename: str, app: App):
    bucket = storage.bucket(app=app)
    blob = bucket.blob(filename)
    return blob.public_url
