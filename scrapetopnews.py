#https://text.npr.org/1001
#https://www.newyorker.com/feed/news
import urllib.request
from bs4 import BeautifulSoup
import json
import requests
from datetime import datetime
import dateutil.parser
import time

import selenium 
from selenium import webdriver
from selenium.webdriver.common.proxy import Proxy, ProxyType
from selenium.webdriver.chrome.options import Options
#https://www.newyorker.com/feed/news


######
###### Parse functions: sift text out of scraped content
######
######
######
def parse_NewYorker(r):
    if(r is None):
        return(None)
    begin = str(r).index("window.cns.pageContext = ")+len("window.cns.pageContext = ")
    end = str(r).index("</script><meta id")
    selected = (str(r)[begin:end])
    selected = withinBrackets(selected)
    #json.loads(selected)
    story = {"author": None, "headline": None, "datePublished": None, "articleBody": None}
    for x in selected:
        x = x.encode().decode("unicode-escape").encode().decode('utf-8')
        try:
            x = json.loads(x)
        except:
            print(x)
            break
        if("author" in x.keys()):
            story['author'] = x['author']
        if("articleBody" in x.keys()):
           story['articleBody'] = x['articleBody']
        if('datePublished' in x.keys()):
           story['datePublished'] = x['datePublished']
        if('headline' in x.keys()):
            story['headline'] = x['headline']
    return(story)

def parse_NYT(r,i):
    if(r is None):
        print("None...")
        return(None)
    story = {"author": i['author'], "headline": i['title'], 'hyperlink': i['link'], "datePublished": i["datePublished"], "articleBody": None,  "publication": "New York Times"}
    soup = BeautifulSoup(r,features="lxml")
    running_samples = []
    for head in soup.find_all("section"):
        for element in head.findAll('p'):
            #print(element.text)
            if(element.text == "We are having trouble retrieving the article content."):
                print("hit")
            else:
                print(i['link'])
                running_samples.append(element.text)
    story["articleBody"] = " ".join(running_samples)
    return(story)

def parse_BBC(r,i):
    if(r is None):
        print("None...")
        return(None)
    story = {"author": i['author'], "headline": i['title'], 'hyperlink': i['link'], "datePublished": i["datePublished"], "articleBody": None,  "publication": "BBC"}
    soup = BeautifulSoup(r,features="lxml")
    running_samples = []
    for body in soup.find_all('div', attrs={"data-component":"byline-block"}):
        for name in body.findAll('div'):
            if name.has_attr('class'):
                if('TextContributorName' in name['class'][0]):
                    if("By" in name.text):
                        if("&" in name.text):
                            story['author'] = name.text.replace("By","").split("&")
                        else:
                            story['author'] = [name.text.replace("By","")]
    for body in soup.find_all('div', attrs={"data-component": "text-block"}):
        
        running_samples.append(body.text)
    print(i['link'])
    story["articleBody"] = " ".join(running_samples)
    return(story)

def parse_NPR(r):
    if(r is None):
        return(None)
    story = {"author": None, "headline": None, "datePublished": None, "articleBody": None, "publication": "NPR"}
    soup = BeautifulSoup(r,features="lxml")
    title = soup.select('h1')[0].text.strip()
    story['headline'] = title
    for head in soup.find_all("div", {"class": "story-head"}):
        for element in head.findAll('p'):
            heading_sample = element.findAll(text = True)
            if(heading_sample is not None and len(heading_sample)!=0):
                if("•" in heading_sample[0]):
                    try:
                        if("Updated" in heading_sample[0]):
                            heading_sample[0]= heading_sample[0].replace("Updated","")
                        heading_sample[0] = heading_sample[0].replace("•", "")
                        d = dateutil.parser.parse(heading_sample[0])
                        story['datePublished'] = d
                    except Exception as e:
                        #print(e)
                        pass
                if("By " in heading_sample[0]):
                    heading_sample[0] = heading_sample[0].replace("By ", "")
                    if("," in heading_sample[0]):
                        story['author'] = heading_sample[0].split(",")
                    else:
                        story['author'] = [heading_sample[0]]
    running_samples = []
    for body in soup.find_all("div", {"class": "paragraphs-container"}):
        for element in body.findAll('p'):
            body_sample = element.findAll(text = True)
            running_samples = running_samples+ body_sample
    story['articleBody'] = " ".join(running_samples)
    return(story)
######
###### Story List functions: determine where to scrape
######
######
######

#get RSS feed from the New Yorker to map articles to retrieve
def buildNewYorkerStoryList(hyperlink):
    url = requests.get(hyperlink)
    soup = BeautifulSoup(url.content, 'xml')
    entries = soup.find_all('item')
    items = []
    for i in entries:
        title = i.title.text
        desc = i.description.text
        link = i.link.text
        items.append({'title':title, 'description': desc, "link": link,  "publication": "New Yorker"})
    return(items)
    
def buildBBCStoryList(hyperlink):
    stories = []
    url = requests.get(hyperlink)
    soup = BeautifulSoup(url.content, 'xml')
    datas = soup.find_all("li")
    items = []
    entries = soup.find_all('item')
    items = []
    for i in entries:
        story = {"author": None, "title": i.title.text, 'link': i.link.text, "datePublished": i.pubDate.text, "articleBody": None,  "publication": "BBC"}
        stories.append(story)
    return(stories)

def buildNPRStoryList(r):
    soup = BeautifulSoup(r, "lxml")
    construct_link = "https://text.npr.org"
    datas = soup.find_all("li")
    items = []
    for data in datas:
        for link in data.find_all('a', href=True):
            #if not in non-story link categories
            if(data.text not in ["News", "Culture", "Music", "Contact Us", "Terms of Use", "Permissions", "Privacy Policy"]):
                items.append({"title": data.text, "link":construct_link+link['href']})
    return(items)

def buildNYTStoryList(hyperlink):
    #https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml
    url = requests.get(hyperlink)
    soup = BeautifulSoup(url.content, 'xml')
    entries = soup.find_all('item')
    items = []
    for i in entries:
        title = i.title.text
        desc = i.description.text
        link = i.link.text
        author = i.find('creator').get_text(strip=True)
        pubdate = i.pubDate.text
        items.append({'title':title, 'description': desc, "link": link, "author": author, "datePublished":pubdate,  "publication": "New York Times"})
    return(items)
##
## General purpuse utility functions
##
##
##
##
## 
def withinBrackets(r):
    jsInSample = True
    iteratedIndex = 5
    stack_start = []
    stack_end = []
    rank = 0
    cuttings = []
    for x in range(0, len(r)):
        if(r[x] == "{"):
            stack_start.append(x)
            #open rank increases
            rank+=1
        elif(r[x] == "}"):
            stack_end.append(x)
            if(rank>0):
                #the last opened is the one being closed
                cutting = [stack_start.pop(), x]
                #append the cutting
                cuttings.append(r[cutting[0]:cutting[1]+1])
                #the last cutting *should probably* be one that encompasses all others, 
                #if such case occurs
            #close a rank
            rank-=1
    return(cuttings)

def retrieveContent(hyperlink):
    hdr = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
    }
    hdr['Connection'] = 'keep-alive' 
    try:
        req = urllib.request.Request(hyperlink, headers=hdr)
        #req.set_proxy('192.111.130.2:4145', 'http')
        req.add_header("Cookie", "sessionActive=true")

        response = urllib.request.urlopen(req)
        if(response.getcode() == 200):
            body = response.read()
        else:
            print ("Unable to get response with Code : %d " % (response.status_code))
            return(-1)
    except Exception as e:
        print(e)
        return(None)
    return(body)

##
## Get frontpage: get sets of frontpages from targeted publications
##
##
##
##
## 
def getFrontpage_ProPublica():
    hyperlink = "https://www.propublica.org/feeds/propublica/main"
    url = requests.get(hyperlink)
    soup = BeautifulSoup(url.content, 'xml')
    entries = soup.find_all('item')
    stories = []
    for entry in entries: 
        title = entry.title.text
        description = entry.description.text
        good_soup = BeautifulSoup(description, features="lxml")
        body = "".join(good_soup.find_all(string=True, recursive=True))
        link = entry.link.text
        pubDate = entry.pubDate.text
        authors = []
        soup = BeautifulSoup(description, features="lxml")
        spans = soup.find_all('span')
        for span in spans:
            authors.append([span.text])
        extracted = {"author": authors, "headline": title, "datePublished": pubDate, "articleBody": body, "hyperlink": link, "publication": "Propublica"}
        stories.append(extracted)
    return(stories)

def getFrontpage_NPR():
    npr = retrieveContent("https://text.npr.org/1001")
    items = buildNPRStoryList(npr)
    listofstories = []
    for i in items:
        print(i['link'])
        r = retrieveContent(i['link'])
        listofstories.append(parse_NPR(r))

    return(listofstories)

def getFrontpage_NewYorker():
    rss = buildNewYorkerStoryList("https://www.newyorker.com/feed/news")
    listofstories = []
    for i in rss:
        print(i['link'])
        r = retrieveContent(i['link'])
        listofstories.append(parse_NewYorker(r))
    return(listofstories)

def getFrontpage_NYT():
    rss = buildNYTStoryList("https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml")
    listofstories = []
    theyreontome = 0
    for i in rss:
        r = retrieveContent(i['link'])
        if(r == -1):
            theyreontome+=1
        else:
            listofstories.append(parse_NYT(r,i))
        time.sleep(5)
        if(theyreontome>=len(rss)/4):
            break
    return(listofstories)


def getFrontpage_BBC():
    rss = buildBBCStoryList("https://feeds.bbci.co.uk/news/world/rss.xml")
    theyreontome = 0
    stories = []
    for i in rss:
        #print(i['link'])
        r = retrieveContent(i['link'])
        i = parse_BBC(r,i)
        stories.append(i)
    return(stories)

def getFrontpage_Politico():
    #https://rss.politico.com/politics-news.xml
    #https://rss.politico.com/congress.xml
    #vvv contrived vvv
    #https://rss.politico.com/defense.xml
    #https://rss.politico.com/energy.xml
    #https://rss.politico.com/economy.xml
    #https://rss.politico.com/healthcare.xml
    pass


##
## Aggregate, clean, format data
##
##
##
##
## 

class newsitem:
    def __init__(self):
        self.title = None # story title (string)
        self.body = None # story body (string)
        self.publisher = None # publisher text (string)
        self.authors = None # (list)

def getFrontpages():
    newyorker = getFrontpage_NewYorker()
    npr = getFrontpage_NPR()
    bbc = getFrontpage_BBC()
    propublica = getFrontpage_ProPublica()
    nyt = getFrontpage_NYT()
    complete = newyorker + npr + bbc + propublica + nyt
    return(complete)
    

complete = getFrontpages()
import datetime
s = datetime.datetime.now().isoformat()

with open("stories_"+str(s)+".txt", "w") as output:
    output.write(str(complete))#https://text.npr.org/1001
#https://www.newyorker.com/feed/news
import urllib.request
from bs4 import BeautifulSoup
import json
import requests
from datetime import datetime
import dateutil.parser
import time

import selenium 
from selenium import webdriver
from selenium.webdriver.common.proxy import Proxy, ProxyType
from selenium.webdriver.chrome.options import Options
#https://www.newyorker.com/feed/news


######
###### Parse functions: sift text out of scraped content
######
######
######
def parse_NewYorker(r):
    if(r is None):
        return(None)
    begin = str(r).index("window.cns.pageContext = ")+len("window.cns.pageContext = ")
    end = str(r).index("</script><meta id")
    selected = (str(r)[begin:end])
    selected = withinBrackets(selected)
    #json.loads(selected)
    story = {"author": None, "headline": None, "datePublished": None, "articleBody": None}
    for x in selected:
        x = x.encode().decode("unicode-escape").encode().decode('utf-8')
        try:
            x = json.loads(x)
        except:
            print(x)
            break
        if("author" in x.keys()):
            story['author'] = x['author']
        if("articleBody" in x.keys()):
           story['articleBody'] = x['articleBody']
        if('datePublished' in x.keys()):
           story['datePublished'] = x['datePublished']
        if('headline' in x.keys()):
            story['headline'] = x['headline']
    return(story)

def parse_NYT(r,i):
    if(r is None):
        print("None...")
        return(None)
    story = {"author": i['author'], "headline": i['title'], 'hyperlink': i['link'], "datePublished": i["datePublished"], "articleBody": None,  "publication": "New York Times"}
    soup = BeautifulSoup(r,features="lxml")
    running_samples = []
    for head in soup.find_all("section"):
        for element in head.findAll('p'):
            #print(element.text)
            if(element.text == "We are having trouble retrieving the article content."):
                print("hit")
            else:
                print(i['link'])
                running_samples.append(element.text)
    story["articleBody"] = " ".join(running_samples)
    return(story)

def parse_BBC(r,i):
    if(r is None):
        print("None...")
        return(None)
    story = {"author": i['author'], "headline": i['title'], 'hyperlink': i['link'], "datePublished": i["datePublished"], "articleBody": None,  "publication": "BBC"}
    soup = BeautifulSoup(r,features="lxml")
    running_samples = []
    for body in soup.find_all('div', attrs={"data-component":"byline-block"}):
        for name in body.findAll('div'):
            if name.has_attr('class'):
                if('TextContributorName' in name['class'][0]):
                    if("By" in name.text):
                        if("&" in name.text):
                            story['author'] = name.text.replace("By","").split("&")
                        else:
                            story['author'] = [name.text.replace("By","")]
    for body in soup.find_all('div', attrs={"data-component": "text-block"}):
        
        running_samples.append(body.text)
    print(i['link'])
    story["articleBody"] = " ".join(running_samples)
    return(story)

def parse_NPR(r):
    if(r is None):
        return(None)
    story = {"author": None, "headline": None, "datePublished": None, "articleBody": None, "publication": "NPR"}
    soup = BeautifulSoup(r,features="lxml")
    title = soup.select('h1')[0].text.strip()
    story['headline'] = title
    for head in soup.find_all("div", {"class": "story-head"}):
        for element in head.findAll('p'):
            heading_sample = element.findAll(text = True)
            if(heading_sample is not None and len(heading_sample)!=0):
                if("•" in heading_sample[0]):
                    try:
                        if("Updated" in heading_sample[0]):
                            heading_sample[0]= heading_sample[0].replace("Updated","")
                        heading_sample[0] = heading_sample[0].replace("•", "")
                        d = dateutil.parser.parse(heading_sample[0])
                        story['datePublished'] = d
                    except Exception as e:
                        #print(e)
                        pass
                if("By " in heading_sample[0]):
                    heading_sample[0] = heading_sample[0].replace("By ", "")
                    if("," in heading_sample[0]):
                        story['author'] = heading_sample[0].split(",")
                    else:
                        story['author'] = [heading_sample[0]]
    running_samples = []
    for body in soup.find_all("div", {"class": "paragraphs-container"}):
        for element in body.findAll('p'):
            body_sample = element.findAll(text = True)
            running_samples = running_samples+ body_sample
    story['articleBody'] = " ".join(running_samples)
    return(story)
######
###### Story List functions: determine where to scrape
######
######
######

#get RSS feed from the New Yorker to map articles to retrieve
def buildNewYorkerStoryList(hyperlink):
    url = requests.get(hyperlink)
    soup = BeautifulSoup(url.content, 'xml')
    entries = soup.find_all('item')
    items = []
    for i in entries:
        title = i.title.text
        desc = i.description.text
        link = i.link.text
        items.append({'title':title, 'description': desc, "link": link,  "publication": "New Yorker"})
    return(items)
    
def buildBBCStoryList(hyperlink):
    stories = []
    url = requests.get(hyperlink)
    soup = BeautifulSoup(url.content, 'xml')
    datas = soup.find_all("li")
    items = []
    entries = soup.find_all('item')
    items = []
    for i in entries:
        story = {"author": None, "title": i.title.text, 'link': i.link.text, "datePublished": i.pubDate.text, "articleBody": None,  "publication": "BBC"}
        stories.append(story)
    return(stories)

def buildNPRStoryList(r):
    soup = BeautifulSoup(r, "lxml")
    construct_link = "https://text.npr.org"
    datas = soup.find_all("li")
    items = []
    for data in datas:
        for link in data.find_all('a', href=True):
            #if not in non-story link categories
            if(data.text not in ["News", "Culture", "Music", "Contact Us", "Terms of Use", "Permissions", "Privacy Policy"]):
                items.append({"title": data.text, "link":construct_link+link['href']})
    return(items)

def buildNYTStoryList(hyperlink):
    #https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml
    url = requests.get(hyperlink)
    soup = BeautifulSoup(url.content, 'xml')
    entries = soup.find_all('item')
    items = []
    for i in entries:
        title = i.title.text
        desc = i.description.text
        link = i.link.text
        author = i.find('creator').get_text(strip=True)
        pubdate = i.pubDate.text
        items.append({'title':title, 'description': desc, "link": link, "author": author, "datePublished":pubdate,  "publication": "New York Times"})
    return(items)
##
## General purpuse utility functions
##
##
##
##
## 
def withinBrackets(r):
    jsInSample = True
    iteratedIndex = 5
    stack_start = []
    stack_end = []
    rank = 0
    cuttings = []
    for x in range(0, len(r)):
        if(r[x] == "{"):
            stack_start.append(x)
            #open rank increases
            rank+=1
        elif(r[x] == "}"):
            stack_end.append(x)
            if(rank>0):
                #the last opened is the one being closed
                cutting = [stack_start.pop(), x]
                #append the cutting
                cuttings.append(r[cutting[0]:cutting[1]+1])
                #the last cutting *should probably* be one that encompasses all others, 
                #if such case occurs
            #close a rank
            rank-=1
    return(cuttings)

def retrieveContent(hyperlink):
    hdr = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
    }
    hdr['Connection'] = 'keep-alive' 
    try:
        req = urllib.request.Request(hyperlink, headers=hdr)
        #req.set_proxy('192.111.130.2:4145', 'http')
        req.add_header("Cookie", "sessionActive=true")

        response = urllib.request.urlopen(req)
        if(response.getcode() == 200):
            body = response.read()
        else:
            print ("Unable to get response with Code : %d " % (response.status_code))
            return(-1)
    except Exception as e:
        print(e)
        return(None)
    return(body)

##
## Get frontpage: get sets of frontpages from targeted publications
##
##
##
##
## 
def getFrontpage_ProPublica():
    hyperlink = "https://www.propublica.org/feeds/propublica/main"
    url = requests.get(hyperlink)
    soup = BeautifulSoup(url.content, 'xml')
    entries = soup.find_all('item')
    stories = []
    for entry in entries: 
        title = entry.title.text
        description = entry.description.text
        good_soup = BeautifulSoup(description, features="lxml")
        body = "".join(good_soup.find_all(string=True, recursive=True))
        link = entry.link.text
        pubDate = entry.pubDate.text
        authors = []
        soup = BeautifulSoup(description, features="lxml")
        spans = soup.find_all('span')
        for span in spans:
            authors.append([span.text])
        extracted = {"author": authors, "headline": title, "datePublished": pubDate, "articleBody": body, "hyperlink": link, "publication": "Propublica"}
        stories.append(extracted)
    return(stories)

def getFrontpage_NPR():
    npr = retrieveContent("https://text.npr.org/1001")
    items = buildNPRStoryList(npr)
    listofstories = []
    for i in items:
        print(i['link'])
        r = retrieveContent(i['link'])
        listofstories.append(parse_NPR(r))

    return(listofstories)

def getFrontpage_NewYorker():
    rss = buildNewYorkerStoryList("https://www.newyorker.com/feed/news")
    listofstories = []
    for i in rss:
        print(i['link'])
        r = retrieveContent(i['link'])
        listofstories.append(parse_NewYorker(r))
    return(listofstories)

def getFrontpage_NYT():
    rss = buildNYTStoryList("https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml")
    listofstories = []
    theyreontome = 0
    for i in rss:
        r = retrieveContent(i['link'])
        if(r == -1):
            theyreontome+=1
        else:
            listofstories.append(parse_NYT(r,i))
        time.sleep(5)
        if(theyreontome>=len(rss)/4):
            break
    return(listofstories)


def getFrontpage_BBC():
    rss = buildBBCStoryList("https://feeds.bbci.co.uk/news/world/rss.xml")
    theyreontome = 0
    stories = []
    for i in rss:
        #print(i['link'])
        r = retrieveContent(i['link'])
        i = parse_BBC(r,i)
        stories.append(i)
    return(stories)

def getFrontpage_Politico():
    #https://rss.politico.com/politics-news.xml
    #https://rss.politico.com/congress.xml
    #vvv contrived vvv
    #https://rss.politico.com/defense.xml
    #https://rss.politico.com/energy.xml
    #https://rss.politico.com/economy.xml
    #https://rss.politico.com/healthcare.xml
    pass


##
## Aggregate, clean, format data
##
##
##
##
## 

class newsitem:
    def __init__(self):
        self.title = None # story title (string)
        self.body = None # story body (string)
        self.publisher = None # publisher text (string)
        self.authors = None # (list)

def getFrontpages():
    newyorker = getFrontpage_NewYorker()
    npr = getFrontpage_NPR()
    bbc = getFrontpage_BBC()
    propublica = getFrontpage_ProPublica()
    nyt = getFrontpage_NYT()
    complete = newyorker + npr + bbc + propublica + nyt
    return(complete)
    

complete = getFrontpages()
import datetime
s = datetime.datetime.now().isoformat()

with open("stories_"+str(s)+".txt", "w") as output:
    output.write(str(complete))
