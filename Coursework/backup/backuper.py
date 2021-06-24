# -*- coding: utf-8 -*-
from pymongo import MongoClient
import json


client = MongoClient("mongodb+srv://dbKLIAT:KLIAT@cluster0.nssdw.mongodb.net/retryWrites=true&w=majority")
db = client.get_database('KLIAT')

collection = db.Articles

cursor = collection.find()

list_cur = list(cursor)
data = []


for i in range(len(list_cur)):
  json_data = ({
    "URL": str(list_cur[i]['URL']),
    "Header": str(list_cur[i]['Header']),
    "Date": str(list_cur[i]['Date']),
    "Time": str(list_cur[i]['Time']),
    "Video and images": list_cur[i]['Video and images'],
    "Article text": u'{}'.format(list_cur[i]['Article text']),
    "Comments": list_cur[i]['Comments']
  })
  data.append(json_data)

print(data)

# Writing data to file data.json
with open('Articles.json', 'w', encoding='utf-8') as file:
  json.dump(data, file, indent=4, ensure_ascii=False)
