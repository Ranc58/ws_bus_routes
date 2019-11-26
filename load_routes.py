import json
import os


def load_routes(directory_path='routes'):
    for filename in os.listdir(directory_path):
        if filename.endswith(".json"):
            filepath = os.path.join(directory_path, filename)
            with open(filepath, 'r', encoding='utf8') as file:
                yield json.load(file)


# def process_routes():
#     t = 0
#     routes = 0
#     for route in load_routes():
#         if t >= 10:
#             t = 0
#             yield routes
#         t +=1
#         routes +=1


# for s in process_routes():
#     print(s)
