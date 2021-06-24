import json
from pymongo import MongoClient

client = MongoClient("mongodb+srv://<Login>:<Password>@cluster0.nssdw.mongodb.net/retryWrites=true&w=majority")
db = client.get_database('NewKLIAT')
collection = db.Sentiments


with open("output.txt", encoding='utf-8') as f:
    content = [line.rstrip('\n') for line in f]
    f.close()

#print(content)

text_to_analyze = []
object_to_analyze = []

for i in range(len(content)):
    if content[i] == "\tData":
        text_to_analyze.append(content[i-1])
    if content[i] == "\t}":
        object_to_analyze.append(content[i-1])


counter = 0
data = []

for i in range(len(text_to_analyze)):
    print(text_to_analyze[i])
    if str(text_to_analyze[i]) == "\t}":
        json_data = ({
            "text": str(text_to_analyze[i - 1]),
            "id": counter
        })
        counter += 1
    else:
        counter += 1
        json_data = ({
            "text": str(text_to_analyze[i]),
            "id": counter
        })
        data.append(json_data)

with open("test_persons.json", "w", encoding="utf-8") as write_file:
    json.dump(data, write_file, ensure_ascii=False, sort_keys=True, indent=4)
    write_file.close()

db_documents = list(collection.find({}))
existing_sentiments = []

for i in range(len(db_documents)):
    existing_sentiments.append(db_documents[i]['id'])

for i in range(len(text_to_analyze)):
    current_id = i + 1
    if current_id not in existing_sentiments:
        print("Creating new document")
        collection.insert_one(({
            "Object": object_to_analyze[i][18:],
            "Text": str(text_to_analyze[i]),
            "id": current_id
        }))
    else:
        print('Document with id {} already exist\n'.format(current_id))
        founded_document = list(collection.find({'id': current_id}))
        if text_to_analyze[i] != founded_document[0].get('Text') and text_to_analyze[i] != "\t}":
            print('Updating text field for sentiment № "{}"...\n'.format(current_id))
            collection.update_one({"id": current_id},
                                  {'$set': {
                                      "Text": text_to_analyze[i]
                                  }})
        if text_to_analyze[i] == founded_document[0].get('Text') and text_to_analyze[i] == "\t}":
            print('Updating text field for sentiment № "{}"...\n'.format(current_id))
            collection.update_one({"id": current_id},
                                  {'$set': {
                                      "Text": text_to_analyze[i-1]
                                  }})