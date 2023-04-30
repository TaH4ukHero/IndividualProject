import json

with open('cities.json', encoding='utf8') as f:
    data = json.load(f)
    data = list(filter(lambda x: x['population'] >= 100_000, data))
    print(list(filter(lambda x: x['population'] >= 300_000, data)))
    with open('cities.txt', 'w', encoding='utf8') as f1:
        for i in data:
            f1.write(f"{i['name']}\n")