import json
import os


def get_route_info(filename, directory_path):
    if filename.endswith(".json"):
        filepath = os.path.join(directory_path, filename)
        with open(filepath, 'r', encoding='utf8') as file:
            yield json.load(file)


def load_routes(directory_path='routes', routes_count=None):
    if routes_count:
        counter = 0
        for filename in os.listdir(directory_path):
            for route in get_route_info(filename, directory_path):
                if counter >= routes_count:
                    return
                counter += 1
                yield route
