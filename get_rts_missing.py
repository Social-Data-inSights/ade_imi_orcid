import requests, os, json, time, csv
import xml.etree.ElementTree as ET
from ade_imi.data_conf import base_data_folder

def get_rts_missing() :
    orcid_folder = base_data_folder + '/orcid/'
    experts_folder = orcid_folder + 'experts/'
    rts_search_folder = experts_folder + 'rts_search/'

    for folder in [orcid_folder, experts_folder, rts_search_folder] :
        if not os.path.exists(folder) :
            os.mkdir(folder)
        
    base_url = 'https://pub.orcid.org/v3.0/'

    #load or create the data
    loaded = []
    for default, filename in [
        ({}, 'rts_xml.json'),
        (set(), 'missing.json'),
        ({}, 'failed_searched_xml.json')
    ] :
        save_file = rts_search_folder + filename
        if os.path.exists(save_file) :
            with open(save_file, encoding='utf8') as f :
                loaded.append(json.load(f))
        else :
            loaded.append(default)
    rts_xml, missing, failed_searched_xml = loaded
    missing = set(missing)

    #load extracted orcid experts and rts experts 
    id2expert_name_file = experts_folder + 'id2expert_name.json'
    with open(id2expert_name_file) as f :
        id2expert_name = json.load(f)
        
    rts_folder = base_data_folder + '/RTS/meta/'
    rts_expert_file = rts_folder + 'expert_info.json'
    with open(rts_expert_file) as f :
        rts_expert = json.load(f)

    #experts missing in orcid
    reverse_name= lambda x : ' '.join(x.split(' ')[::-1])
    missing_experts = (set(rts_expert) - ({ reverse_name(expert) for expert in id2expert_name.values() if expert}))

    #get best search for each experts
    for i, expert in enumerate(missing_experts) :
        info_expert = rts_expert[expert]
        if not i % 100 :
            print(i, expert, time.ctime())
        if not expert in rts_xml and not expert in missing:
            if "first_name" in info_expert and "last_name" in info_expert:
                
                url = base_url + f'search?q=given-names:("{info_expert["first_name"]}")&family-name=("{info_expert["last_name"]}")'
                xml_res = requests.get(url).text
                root = ET.fromstring( xml_res)

                if len(root) :
                    orcid = root[0][0][1].text
                    rts_xml[expert] = requests.get(base_url + f'{orcid}/record').text
                else :
                    missing.add(expert)

    to_add_missing = set()
    rts_name2orcid_name = {}
    probs = [0] * 7
    for expert, xml in rts_xml.items() :
        root = ET.fromstring( xml)
        if not root :
            probs[0] += 1
            rts_name2orcid_name[expert] = None
            to_add_missing.add(expert)
            continue
        person_elem = root.find('{http://www.orcid.org/ns/person}person')
        if not person_elem :
            probs[1] += 1
            rts_name2orcid_name[expert] = None
            to_add_missing.add(expert)
            continue
        name_elem = person_elem.find('{http://www.orcid.org/ns/person}name')
        orc_firstname_elem = name_elem.find('{http://www.orcid.org/ns/personal-details}given-names')
        orc_lastname_elem = name_elem.find( '{http://www.orcid.org/ns/personal-details}family-name') 
        if orc_firstname_elem is None or orc_lastname_elem is None :
            probs[2] += 1
            rts_name2orcid_name[expert] = None
            to_add_missing.add(expert)
        else :
            orc_firstname, orc_lastname = orc_firstname_elem.text, orc_lastname_elem.text
            rts_name2orcid_name[expert] = f'{orc_firstname} {orc_lastname}'
            info_expert = rts_expert[expert]
            if not (orc_firstname == info_expert['first_name'] and orc_lastname == info_expert['last_name']) :
                probs[-1] += 1
                to_add_missing.add(expert)
            else :
                probs[3] += 1
                print(expert, root.attrib)

    print(probs)

    failed_searched_xml = {}
    for expert in to_add_missing :
        failed_searched_xml[expert] = rts_xml[expert]
        missing.add(expert)
        del rts_xml[expert]
    
    for to_dump, namefile in [
        (rts_xml, 'rts_xml.json'),
        (list(missing), 'missing.json'),
        (failed_searched_xml, 'failed_searched_xml.json'),
        (rts_name2orcid_name, 'rts_name2orcid_name.json'),
    ] :
        with open(rts_search_folder+namefile, 'w', encoding='utf8') as f :
            json.dump(to_dump, f)


if __name__ == '__main__' :
    get_rts_missing()