'''
Donwload grid_id at https://www.grid.ac/downloads

good api : https://info.orcid.org/documentation/api-tutorials/api-tutorial-searching-the-orcid-registry/#Formatting_search_queries

also usefull :https://github.com/ORCID/orcid-model/tree/master/src/main/resources/record_3.0
'''

import requests, os, json, time, csv
import xml.etree.ElementTree as ET

from ade_imi.data_conf import base_data_folder

def download_by_organisation(experts_folder, grid_id_csv, base_url = 'https://pub.orcid.org/v3.0/') :
    '''
    Download the experts ids by the organisations they belong to
    '''
    by_organisation_file = experts_folder+'by_organisation.json'
    if os.path.exists(by_organisation_file) :
        print('by_organisation already done ')
        with open(experts_folder+'all_orcid.json') as f :
            all_orcid = set(json.load(f))
        with open(by_organisation_file) as f :
            by_organisation = json.load(f)
        return all_orcid, by_organisation

    organisation2grid_id= {}
    with open(grid_id_csv, encoding='utf8') as f :
        csv_reader = csv.reader(f)
        for ID,Name,_,_,Country in csv_reader :
            if Country == 'Switzerland' :
                organisation2grid_id[Name] =  ID

    organisations2ringgold = {
        "CHUV" : 30635, 
        "EPFL": 27218, 
        "HES-SO-Geneve": 128870, 
        "HES-SO-Fribourg": 128872, 
        "HUG": 27230, 
        "IDIAP": 226188, 
        "IHEID_1": 30525, 
        "IHEID_2": 548993, 
        "SIB_1": 30489, 
        "SIB_1": 30488, 
        "UNIGE": 27212, 
        "UNIL": 27213, 
        "UNINE": 27214
    }

    all_orcid = set()
    by_organisation = {}

    for institution_to_val, get_url in [
        (organisations2ringgold, lambda val, start : f'search?q=ringgold-org-id:{val}&start={start}' ),
        (organisation2grid_id, lambda val, start : f'search?q=grid-org-id:{val}&start={start}' ),
    ] :
        for organisation, val in institution_to_val.items() :
            print(organisation)
            num_found = None
            start = 0
            curr = []
            while num_found is None or len(curr)< num_found :
                if start > 0 :
                    print(start, num_found, len(curr))
                res = requests.get(base_url + get_url(val, start)).text
                root = ET.fromstring(res)
                
                if num_found is None :
                    num_found = int(root.attrib['num-found'])
                
                
                for child in root:
                    assert child[0][1].tag == '{http://www.orcid.org/ns/common}path'
                    curr.append(child[0][1].text)
                start=len(curr)

            if curr :
                all_orcid.update(set(curr))
                by_organisation[organisation] = by_organisation.get(organisation, []) + curr
            print(organisation, len(curr))

    with open(experts_folder+'all_orcid.json' , 'w' ) as f :
        json.dump(list(all_orcid) , f)
        
    with open(by_organisation_file , 'w' ) as f :
        json.dump(by_organisation , f)

    return all_orcid, by_organisation

def download_id2xml(all_orcid, experts_folder, base_url = 'https://pub.orcid.org/v3.0/') :
    '''
    get the expert information from their ids
    '''
    id2exp_xml_file = experts_folder + 'id2exp_xml.json'
    if os.path.exists(id2exp_xml_file) :
        with open(id2exp_xml_file, encoding='utf8' ) as f :
            id2exp_xml = json.load(f)
    else :
        id2exp_xml = {}

    t = time.time()
    for i, id_ in enumerate(all_orcid) :
        
        if not id_ in id2exp_xml :
            id2exp_xml[id_] = requests.get(base_url + f'{id_}/record').text
            if not i % 100 and i :
                print(i,id_,len(all_orcid), (time.time()-t) / 100)
                t = time.time()
                with open(experts_folder + 'id2exp_xml-backup.json' , 'w', encoding='utf8') as f :
                    json.dump(id2exp_xml, f)
                with open(experts_folder + 'id2exp_xml.json' , 'w', encoding='utf8') as f :
                    json.dump(id2exp_xml, f)

    with open(experts_folder + 'id2exp_xml.json' , 'w', encoding='utf8') as f :
        json.dump(id2exp_xml, f)
    return id2exp_xml

def xml_to_json_it (xml) :
    tags= {tag.tag for tag in xml}
    if tags :
        res = {}
        for tag in tags :
            to_add_tag = []
            for tag_content in xml.findall(tag) :
                sub_json = xml_to_json_it (tag_content) 
                if sub_json :
                    to_add_tag.append(sub_json)
            if to_add_tag :
                idx_tag = tag.split('}')[1]
                if len(to_add_tag) == 1 :
                    to_add_tag = to_add_tag[0]
                res[idx_tag] = to_add_tag
        return res
    else :
        text = xml.text
        return str(text.strip()) if text else ''

def xml_to_json(id2exp_xml, experts_folder) :
    '''
    expert id -> name : work description
    '''
    expert_articles_file = experts_folder + 'expert_articles.json'
    if os.path.exists(expert_articles_file) :
        with open(expert_articles_file) as f :
            expert_articles = json.load(f)
    else :
        expert_articles = {}
    no_work = []
    for orcid,xml in id2exp_xml.items() :
        if not orcid in expert_articles :
            if 'work:work-summary' in xml :
                root = ET.fromstring(xml)

                articles = []
                for group in  root.find('{http://www.orcid.org/ns/activities}activities-summary')\
                    .find('{http://www.orcid.org/ns/activities}works')\
                    .findall('{http://www.orcid.org/ns/activities}group') :
                    for work in group.findall('{http://www.orcid.org/ns/work}work-summary') :
                        #work_details = {tag.tag.split('}')[1] : work.find(tag.tag).text.strip() for tag in work if work.find(tag.tag).text and work.find(tag.tag).text.strip()}
                        work_details=xml_to_json_it(work)
                        if work_details :
                            articles.append(work_details)

                if articles :
                    persons_branch = root.find('{http://www.orcid.org/ns/person}person').find('{http://www.orcid.org/ns/person}name')
                    if persons_branch :
                        first_name = persons_branch.find('{http://www.orcid.org/ns/personal-details}given-names')
                        last_name  = persons_branch.find('{http://www.orcid.org/ns/personal-details}family-name')
                        if first_name and last_name :
                            name = f"{first_name.text} {last_name.text}"
                        else :
                            name = orcid
                    else :
                        name = orcid

                    expert_articles[name] = articles
                else :
                    no_work.append(orcid)

    with open(expert_articles_file, 'w' ) as f :
        json.dump(expert_articles, f)
    return expert_articles

def get_id2expert_name(expert_articles, experts_folder) :
    id2expert_name_file = experts_folder + 'id2expert_name.json'
    if os.path.exists(id2expert_name_file) :
        with open(id2expert_name_file) as f :
            id2expert_name = json.load(f)
    else :
        id2expert_name = {}

    t = time.time()
    url_info_expert = 'https://orcid.org/%s/public-record.json'
    for i, orcid in enumerate(expert_articles) :
        if not orcid in id2expert_name :
            name = requests.get(url_info_expert%orcid).json()['displayName']
            id2expert_name[orcid] = name

            if not i % 100 and i :
                print(i,orcid,len(id2expert_name), (time.time()-t) / 100)
                t = time.time()
                with open(id2expert_name_file , 'w') as f :
                    json.dump(id2expert_name, f)

    with open(id2expert_name_file, 'w' ) as f :
        json.dump(id2expert_name, f)

    return id2expert_name

def main_download_orcid() :
    orcid_folder = base_data_folder + '/orcid/'
    experts_folder = orcid_folder + 'experts/'
    grid_id_csv = orcid_folder + 'grid_id/grid.csv'

    for folder in [orcid_folder, experts_folder] :
        if not os.path.exists(folder) :
            os.mkdir(folder)

    all_orcid, _ = download_by_organisation(experts_folder, grid_id_csv)
    id2exp_xml = download_id2xml(all_orcid, experts_folder)
    del all_orcid
    expert_articles = xml_to_json(id2exp_xml, experts_folder)
    del id2exp_xml
    get_id2expert_name(expert_articles, experts_folder)

if __name__ == '__main__' :
    main_download_orcid()