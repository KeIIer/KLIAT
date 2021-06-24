from pymongo import MongoClient
import re

client = MongoClient("mongodb+srv://<Login>:<Password>@cluster0.nssdw.mongodb.net/retryWrites=true&w=majority")
db = client.get_database('NewKLIAT')
collection = db.Articles

db_documents = list(collection.find({}))

with open('Articles.txt', 'w', encoding="utf-8") as f:
    for i in range(len(list(db_documents))):
        print(db_documents[i]['Header'])
        print(db_documents[i]['Article text'])
        f.write('Статья номер {} \n'.format(i+1))
        f.write(db_documents[i]['Header'])
        f.write('\n')
        f.write(re.sub(r'\', \'', ' ', str(db_documents[i]['Article text'])))
        f.write('\n\n')
    f.close()
