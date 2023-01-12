import requests, os, json, time, csv, requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from collections import Counter

from ade_imi.data_conf import base_data_folder

def download_if_not_exists(url, save_file) :
    if os.path.exists(save_file) :
        with open(save_file, encoding='utf8') as f :
            return f.read()
    else :
        try :
            html = requests.get(url)
            with open(save_file, 'w', encoding='utf8') as f :
                f.write(html.text)
            return html.text
        except requests.exceptions.ConnectionError :
            with open(save_file, 'w', encoding='utf8') as f :
                f.write('')
            return ''

def clean_arxiv(arxiv_elem) :
    return f'arxiv__{arxiv_elem}.html'.replace('/', '_').replace('arXiv:', '')

def download_arxiv(arxiv_elem, html_folder) :
    arxiv_base = 'https://arxiv.org/abs/'
    url = arxiv_base + arxiv_elem
    save_file = html_folder + clean_arxiv(arxiv_elem)

    if not os.path.exists(save_file) and arxiv_elem.startswith('http') :
        with open(save_file, 'w', encoding='utf8') as f :
            f.write('')
        return None
    else :
        return download_if_not_exists(url, save_file)
            

def arxiv_get_(arxiv_html):
    soup = BeautifulSoup(arxiv_html.text, 'html.parser')
    return max([meta['content'].strip().replace('\n', ' ') for meta in soup.find_all('meta', {'name': 'citation_abstract'})])


def download_bibcode(arxiv_elem, html_folder) :
    pass

def main_get_orcid_content():
    orcid_folder = base_data_folder + 'orcid/'
    experts_folder = orcid_folder + 'experts/'
    html_folder = orcid_folder + 'html/'
    expert_articles_file = experts_folder + 'expert_articles.json'

    for folder in [orcid_folder, experts_folder, html_folder] :
        if not os.path.exists(folder) :
            os.mkdir(folder)
    
    with open(expert_articles_file) as f :
        id2expert_name = json.load(f)

    for works in id2expert_name.values() :
        for work in works :
            if 'external-ids' in work :
                links = work['external-ids']['external-id']
                if links :
                    if not type(links) is list :
                        links = [links]
                    for link in links :
                        arxiv_elem = link['external-id-value']
                        if link['external-id-type'] == 'arxiv' :
                            download_arxiv(arxiv_elem, html_folder)
                        elif link['external-id-type'] == 'bibcode' :
                            download_bibcode(arxiv_elem, html_folder)

if __name__ == '__main__' :
    main_get_orcid_content()