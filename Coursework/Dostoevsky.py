from dostoevsky.tokenization import RegexTokenizer
from dostoevsky.models import FastTextSocialNetworkModel
import json
from pymongo import MongoClient

client = MongoClient("mongodb+srv://<Login>:<Password>@cluster0.nssdw.mongodb.net/retryWrites=true&w=majority")
db = client.get_database('NewKLIAT')
test_collection = db.Sentiments
dostoevsky_collection = db.DostoevskySentiments

x_test, test_inds = [], []
db_test_data = list(test_collection.find({}))

for i in range(len(list(db_test_data))):
    x_test.append(db_test_data[i]['Text'])
    test_inds.append(db_test_data[i]['id'])

tokenizer = RegexTokenizer()
tokens = tokenizer.split('всё очень плохо')  # [('всё', None), ('очень', None), ('плохо', None)]

model = FastTextSocialNetworkModel(tokenizer=tokenizer)

print('Test sentences: {}'.format(len(x_test)))

results = model.predict(x_test, k=2)
sentiments = []

for message, sentiment in zip(x_test, results):
    sentiments.append(sentiment)
    print(message, '->', sentiment)


results_ids = []
results_data = list(dostoevsky_collection.find({}))

if results_data:
    for i in range(len(results_data)):
        results_ids.append(results_data[i]['id'])

for i in range(len(list(db_test_data))):
    current_id = i + 1
    if current_id not in results_ids:
        print("Creating new document")
        dostoevsky_collection.insert_one(({
            "text": str(x_test[i]),
            "id": test_inds[i],
            "sentiment": str(sentiments[i])
        }))
    else:
        print('Document with id {} already exist\n'.format(current_id))
        founded_document = list(dostoevsky_collection.find({'id': current_id}))
        if x_test[i] != founded_document[0].get('text'):
            print('Updating text field for document № "{}"...\n'.format(current_id))
            dostoevsky_collection.update_one({"id": current_id},
                                  {'$set': {
                                      "text": str(x_test[i])
                                  }})
        if str(sentiments[i]) != str(founded_document[0].get('sentiment')):
            print('Updating sentiment field for document № "{}"...\n'.format(current_id))
            dostoevsky_collection.update_one({"id": current_id},
                                  {'$set': {
                                      "sentiment": str(sentiments[i])
                                  }})