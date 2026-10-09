import yaml
from yaml.loader import SafeLoader
# Открываем файл
with open('config.yml') as f:
    # читаем документ YAML
    data = yaml.load(f, Loader=SafeLoader)
    print(list(data.keys())[0])
    print(data)