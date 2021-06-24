import numpy as np
import pandas as pd
import json
import os
from keras.models import Model
from keras.layers import *
from keras.callbacks import EarlyStopping
#from keras.models import Sequential
#from keras.preprocessing.text import Tokenizer
from keras.preprocessing.text import Tokenizer
from keras.preprocessing.sequence import pad_sequences
from keras.utils.np_utils import to_categorical
from pymongo import MongoClient

client = MongoClient("mongodb+srv://<Login>:<Password>@cluster0.nssdw.mongodb.net/retryWrites=true&w=majority")
db = client.get_database('NewKLIAT')
test_collection = db.Sentiments
result_collection = db.AnalyzedSentiments

#test_file = 'test_persons.json'
train_file = 'train.json'

x_train, y_train, x_test, test_inds = [], [], [], []

db_test_data = list(test_collection.find({}))

for i in range(len(list(db_test_data))):
    x_test.append(db_test_data[i]['Text'])
    test_inds.append(db_test_data[i]['id'])

'''with open(test_file, encoding='utf-8') as json_file:
    data = json.load(json_file)

    for row in data:
        x_test.append(row['text'])
        test_inds.append(row['id'])'''

with open(train_file, encoding='utf-8') as json_file:
    data = json.load(json_file)

    for row in data:
        sentiment = -1

        if row['sentiment'] == 'negative':
            sentiment = 0
        elif row['sentiment'] == 'neutral':
            sentiment = 1
        else:
            sentiment = 2

        if sentiment == -1:
            continue

        x_train.append(row['text'])
        y_train.append(sentiment)


print('Train sentences: {}'.format(len(x_train)))
print('Train labels: {}'.format(len(y_train)))
print('Test sentences: {}'.format(len(x_test)))

max_length = 5000
max_features = 20000
embedding_dim = 300

x_all = []
x_all.extend(x_test)
x_all.extend(x_train)

tk = Tokenizer(num_words=max_features, lower=True, filters='\n\t')
tk.fit_on_texts(x_all)
x_train_seq = tk.texts_to_sequences(x_train)
x_test_seq = tk.texts_to_sequences(x_test)

np_x_train = pad_sequences(x_train_seq, maxlen=max_length,  padding='post')
np_x_test = pad_sequences(x_test_seq, maxlen=max_length,  padding='post')
np_y_train = to_categorical(y_train)

class_num = np_y_train.shape[1]

print ('np_x_train shape: {}'.format(np_x_train.shape))
print ('np_x_test shape: {}'.format(np_x_test.shape))
print ('np_y_train shape: {}'.format(np_y_train.shape))

def one_input_classifier(max_length, max_features, embedding_dim, class_num):
    inputs = Input(shape=(max_length,), name='input_1')
    embeddings = Embedding(max_features, embedding_dim, input_length=max_length, name='embedding_1')(inputs)

    conv_1 = Conv1D(32, 9, activation='relu', name='conv1d_1')(embeddings)
    maxpool_1 = MaxPooling1D(16, name='maxpool1d_1')(conv_1)
    dropout_1 = Dropout(0.2, name='dropout_1')(maxpool_1)

    conv_2 = Conv1D(32, 7, activation='relu', name='conv1d_2')(dropout_1)
    maxpool_2 = MaxPooling1D(8, name='maxpool1d_2')(conv_2)
    dropout_2 = Dropout(0.2, name='dropout_2')(maxpool_2)

    bilstm = Bidirectional(LSTM(32, dropout=0.2, recurrent_dropout=0.2, name='lstm_1'),
        name='bidirectional_1')(dropout_2)
    preds = Dense(class_num, activation='softmax', name='preds')(bilstm)

    model = Model(inputs=inputs, outputs=preds)
    model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])
    return model

early_stopping = EarlyStopping(monitor='val_loss', min_delta=0, patience=0, verbose=1,
                               mode='min', baseline=None, restore_best_weights=True)

models = []
classifier_num = 10

for i in range(classifier_num):
    model = one_input_classifier(max_length, max_features, embedding_dim, class_num)

    if i == 0:
        print(model.summary())

    model.fit(np_x_train, np_y_train, validation_split=0.3, shuffle=True,
              callbacks=[early_stopping], epochs=10, batch_size=32, verbose=1)
    models.append(model)

y_pred_list = []

for i in range(classifier_num):
    y_pred = models[i].predict(np_x_test, batch_size=32, verbose=1)
    y_pred_list.append(y_pred)

print(len(y_pred_list))

test_num = np_x_test.shape[0]
y_pred = np.ndarray(shape=(test_num,), dtype=np.int32)

for i in range(test_num):
    votes = []

    for j in range(classifier_num):
        vote = y_pred_list[j][i].argmax(axis=0).astype(int)
        votes.append(vote)

    vote_final = max(set(votes), key=votes.count)
    y_pred[i] = vote_final

predicted_classes = []

for i, y_val in enumerate(y_pred):
    if y_val == 0:
        predicted_classes.append((test_inds[i], 'negative'))
    elif y_val == 1:
        predicted_classes.append((test_inds[i], 'neutral'))
    else:
        predicted_classes.append((test_inds[i], 'positive'))

output_data = []

for i in range(len(predicted_classes)):
    json_data = ({
        "text": x_test[i],
        "id": test_inds[i],
        "sentiment": str(predicted_classes[i][1])
    })
    output_data.append(json_data)

with open("persons_analyzed.json", "w", encoding="utf-8") as write_file:
    json.dump(output_data, write_file, ensure_ascii=False, sort_keys=True, indent=4)
    write_file.close()


results = list(result_collection.find({}))
results_id = []
print(predicted_classes)
print(predicted_classes[0])
print(predicted_classes[0][0], predicted_classes[1][0], predicted_classes[0][1], predicted_classes[1][1])

for i in range(len(results)):
    results_id.append(results[i]['id'])

for i in range(len(list(db_test_data))):
    current_id = i + 1
    if current_id not in results_id:
        print("Creating new document")
        result_collection.insert_one(({
            "text": str(x_test[i]),
            "id": test_inds[i],
            "sentiment": str(predicted_classes[i][1])
        }))
    else:
        print('Document with id {} already exist\n'.format(current_id))
        founded_document = list(result_collection.find({'id': current_id}))
        if x_test[i] != founded_document[0].get('text'):
            print('Updating text field for document № "{}"...\n'.format(current_id))
            result_collection.update_one({"id": current_id},
                                  {'$set': {
                                      "text": str(x_test[i])
                                  }})
        if str(predicted_classes[i][1]) != str(founded_document[0].get('sentiment')):
            print('Updating sentiment field for document № "{}"...\n'.format(current_id))
            result_collection.update_one({"id": current_id},
                                  {'$set': {
                                      "sentiment": str(predicted_classes[i][1])
                                  }})
