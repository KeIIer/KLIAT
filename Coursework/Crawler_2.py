# encode UTF-8
import requests
from bs4 import BeautifulSoup
import re
import json
from pymongo import MongoClient
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options


def get_main_info(div_array, items, regexp, uni_reg):
    for i in range(len(div_array)):
        items.append(re.findall(regexp, str(div_array[i])))
        items[i] = re.sub(uni_reg, '', str(items[i]))
    return items


def get_detailed_links(url, links, detailed_link_array):
    for i in range(len(links)):
        detailed_link_array.append(url + str(links[i]))
    return detailed_link_array


def get_article_source(article_url, driver):
    driver.get(article_url)
    content = driver.page_source
    # unparsedURL = requests.get(article_url)
    # parsedURL = BeautifulSoup(unparsedURL.content, 'html.parser')
    parsedURL = BeautifulSoup(content, 'html.parser')
    div = parsedURL.find_all("div", {"class": "n-text"})
    comments = re.findall(r'data-identity=".*">(.*?)<', str(content))[0]
    # print(comments)
    # print(div)
    # video_and_image = re.findall(r'src="(.*?)\ ', str(div))
    video_and_image = re.findall(r'src="(.*?)\ ', str(div))
    for i in range(len(video_and_image)):
        video_and_image[i] = re.sub(r'\"', '', video_and_image[i])
    if video_and_image:
        print('Video or image found: {}'.format(video_and_image))
    else:
        video_and_image = 'Not found'
    article_text = re.findall(r'<div>(.*?)\n', str(div))
    return article_text, video_and_image, str(comments)


def main():
    print('Getting articles...')
    client = MongoClient("mongodb+srv://<Login>:<Password>@cluster0.nssdw.mongodb.net/retryWrites=true&w=majority")
    db = client.get_database('NewKLIAT')
    collection = db.Articles
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')

    URL = 'https://v102.ru'
    page = requests.get(URL)
    soup = BeautifulSoup(page.content, 'html.parser')

    json_data = ({
        "URL": "",
        "Header": "",
        "Date": "",
        "Time": "",
        "Video and images": "",
        "Article text": ""
    })

    '''
    divs
    new-article
    '''
    mydivs = soup.find_all("div", {"class": "new-article"})
    mydivs = list(mydivs)
    print("Number of found articles: ", len(mydivs))

    regexes = [r'headline">(.*?)<',
               r'date-new">(.*?)<',
               r'([0-2][0-9]\:[0-5][0-9])',
               r'"detail-link-text" href="(.*?)\"']

    uni_regex = r'[\[\]\']'

    # Getting main info

    headers = get_main_info(mydivs, [], regexes[0], uni_regex)
    date_stamps = get_main_info(mydivs, [], regexes[1], uni_regex)
    time_stamps = get_main_info(mydivs, [], regexes[2], uni_regex)
    partial_links = get_main_info(mydivs, [], regexes[3], uni_regex)
    detail_links = get_detailed_links(URL, partial_links, [])

    text, video_image_source, comments = ['Not found'] * len(detail_links), \
                                         ['Not found'] * len(detail_links), \
                                         ['Not found'] * len(detail_links)

    # Getting article sources

    print('Getting article sources')
    driver = webdriver.Chrome(ChromeDriverManager().install(), options=chrome_options)

    for i in range(len(detail_links)):
        text[i], video_image_source[i], comments[i] = get_article_source(detail_links[i], driver)
    driver.quit()
    for i in range(len(text)):
        for j in range(len(text[i])):
            # print(text[i][j])
            text[i][j] = re.sub(r'<.*?>|\\.?', '', str(text[i][j]))
            text[i][j] = text[i][j].replace('\r', '')
            # print(text[i])

    for i in range(len(text)):
        text[i] = list(filter(lambda item: item, text[i]))
        text[i] = '\n'.join([str(text[i])])
        text[i] = re.sub(r'\[\'|\'\]|', '', str(text[i]))
        text[i] = re.sub(r'\'\,\ \'|\'\ \,\ \'', ' ', str(text[i]))
        text[i] = text[i].replace(u'\\xa0', u' ')
        # print(text[i])

    print('\nDumping to json file\n')
    with open("data_file.json", "w", encoding="utf-8") as write_file:
        for i in range(len(detail_links)):
            json_data = ({
                "URL": detail_links[i],
                "Header": headers[i],
                "Date": date_stamps[i],
                "Time": time_stamps[i][:5],
                "Video and images": video_image_source[i],
                "Article text": text[i],
                "Comments": comments[i]
            })

            json.dump(json_data, write_file, ensure_ascii=False, indent=4)

    db_documents = list(collection.find({}))
    db_URLs = []

    print('Working with database...\n')

    for i in range(len(list(db_documents))):
        db_URLs.append(db_documents[i]['URL'])

    for i in range(len(detail_links)):
        if detail_links[i] not in db_URLs:
            print("Creating new document")
            collection.insert_one(({
                "URL": detail_links[i],
                "Header": headers[i],
                "Date": date_stamps[i],
                "Time": time_stamps[i][:5],
                "Video and images": video_image_source[i],
                "Article text": text[i],
                "Comments": comments[i]
            }))
        else:
            print('Iteration {} out of {}'.format(i + 1, len(detail_links)))
            founded_document = list(collection.find({'URL': detail_links[i]}))
            print('Document with header "{}" already exist'.format(headers[i]))
            print('DB article: "{}", founded article "{}"'.format(founded_document[0].get('Header'),
                                                                  headers[i]))
            print('DB article URL: "{}", founded article URL "{}"'.format(founded_document[0].get('URL'),
                                                                          detail_links[i]))
            print('DB article comments: "{}", founded article comments "{}"\n'.format(
                founded_document[0].get('Comments'),
                comments[i]))
            if comments[i] != founded_document[0].get('Comments'):
                print('Updating comments field for "{}"...\n'.format(headers[i]))
                collection.update_one({"URL": detail_links[i]},
                                      {'$set': {
                                          "Comments": comments[i]
                                      }})
            if text[i] != founded_document[0].get('Article text'):
                print('Updating text field for "{}"...\n'.format(headers[i]))
                collection.update_one({"URL": detail_links[i]},
                                      {'$set': {
                                          "Article text": text[i]
                                      }})
    print('Process finished')


if __name__ == "__main__":
    main()
