from useful_func import get_desc_of_town

towns = [i.strip() for i in open('cities.txt', encoding='utf8')]
true_towns = []
for i in towns:
    temp = get_desc_of_town(i)
    if temp[0] != 'К сожалению статьи не будет':
        true_towns += [i]
with open('true_towns', 'w', encoding='utf8') as f:
    f.write('\n'.join(true_towns))
