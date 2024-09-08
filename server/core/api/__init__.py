import json, os
__this_dir = os.path.dirname(__file__)

S2C = json.load(
    open(os.path.join(__this_dir, 's2c.json'), 'r')
)
BROADCAST = json.load(
    open(os.path.join(__this_dir, 'broadcast.json'), 'r')
)

def format(Api:dict, **kwargs) -> str:
    '''Format API'''
    # Remove tips and return_type
    Api.pop('tips', None)
    Api.pop('return_type', None)
    # Format with kwargs
    for key, value in kwargs.items():
        if key in Api.keys():
            if isinstance(value, bool):
                value = int(value)
            if Api[key] == '{}':
                Api[key] = Api[key].format(value)
            else:
                Api[key] = value
        else:
            print(f'Error: Key "{key}" not exists')
    for key, value in Api.items():
        if value == '{}':
            print(f'Error: Key "{key}" not formatted')
    return json.dumps(Api)

def red(string:str) -> str:
    '''Red color'''
    return f'\033[91m{string}\033[0m'

def yellow(string:str) -> str:
    '''Yellow color'''
    return f'\033[93m{string}\033[0m'

def green(string:str) -> str:
    '''Green color'''
    return f'\033[92m{string}\033[0m'   