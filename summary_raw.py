
import json, os, time
from shutil import rmtree
import xml.etree.ElementTree as ET
from ade_imi.data_conf import base_data_folder

def xml_to_json (xml) :
    tags= [tag.tag for tag in xml] 
    if tags :
        stags = set(tags)
        if len(tags) != len(stags) :
            assert len(stags) == 1
            res = [] 
        else :
            res = {} 
        for tag in tags :
            sub_json = xml_to_json (xml.find(tag)) 
            if sub_json :
                if type(res) is list :
                    res.append([tag.split('}')[1],sub_json])
                else :
                    res[tag.split('}')[1]] = sub_json
        return res
    else :
        text = xml.text
        return text.strip() if text else text



def lighten(dump) :
    light_dump = {}
    for idx, d in dump.items() :
        works = d.get('works')
        if not works :
            light_dump[idx] = d
            continue

        new_works = []
        for work in works :
            if 'contributors' in work and len(work['contributors']) > 2 :
                new_cont = []
                assert type(work['contributors']) is list, work['contributors']
                for contributor in work['contributors'] :
                    if not contributor in new_cont :
                        new_cont.append(contributor)
                work['contributors'] = new_cont

            if 'citation' in work :
                del work['citation']


            new_works.append(work)
        d['works'] = new_works
        light_dump[idx] = d
    return light_dump

def decompress_tar_gz (save_folder,dump_name , ) :
    if not os.path.exists (save_folder+dump_name) :
        os.system('tar -xzf %s -C %s'%(save_folder+dump_name+'.tar.gz' , save_folder))
    else :
        print('already decompressed', dump_name)

def delete_all_folder (folder) :
    for f in os.listdir(folder) :
        if os.path.isdir(folder + f):
            delete_all_folder (folder + f+'/')
        else :
            os.remove(folder + f)
    rmtree(folder )


def summary_raw (decompress_ids ) :
    raw_folder = base_data_folder + 'orcid/raw/'
    summary_folder = raw_folder+'ORCID_2020_10_activities/'
    
    if not os.path.exists(summary_folder) :
        os.mkdir(summary_folder)
    for decompress_id in decompress_ids:
        summary_raw_it(decompress_id)
    
def decompress_id_is_done (decompress_id,summary_folder) :
    print([
        os.path.exists(summary_folder + "{:02d}".format(i) + str(decompress_id) + '.json')
        for i in range(100)
    ])
    return all([
        os.path.exists(summary_folder + "{:02d}".format(i) + str(decompress_id) + '.json')
        for i in range(100)
    ])

def summary_raw_it(decompress_id) :
    raw_folder = base_data_folder + 'orcid/raw/'
    summary_folder = raw_folder+'ORCID_2020_10_activities/'
    
    base_decompress = 'ORCID_2020_10_activities_%s'
    decompressed_folder = base_decompress%(str(decompress_id))
    if decompress_id_is_done (decompress_id,summary_folder) :
        print(decompressed_folder, 'already done')
    else :
        print(decompressed_folder, 'start')
        if not os.path.exists(raw_folder + decompressed_folder) :
            decompress_tar_gz(raw_folder, decompressed_folder)
        for group_folder in os.listdir(raw_folder + decompressed_folder) :
            res_file = summary_folder+group_folder+'.json'
            if os.path.exists(res_file) :
                print(group_folder, 'already done')
            else :
                res = {}
                print(group_folder, time.ctime())
                group_path = raw_folder + decompressed_folder + '/' + group_folder + '/'
                for orcid in os.listdir(group_path) :
                    curr = {}
                    for info_type in os.listdir(group_path+orcid+'/') :
                        info_type_path = group_path+orcid+'/'+info_type+'/'
                        info_data = []
                        for filedata in os.listdir(info_type_path) :
                            sub_json = xml_to_json(ET.parse(info_type_path+filedata).getroot())
                            if sub_json : 
                                info_data.append(sub_json)

                        curr[info_type] = info_data
                    res[orcid] = curr
                res = lighten(res)
                with open(summary_folder+group_folder+'.json' ,'w' , encoding='utf8') as f :
                    json.dump(res, f)
        delete_all_folder(raw_folder + decompressed_folder+'/')


if __name__ == '__main__' :
    summary_raw(list(range(10)) + ['X'] )
    #summary_raw([i for i in range(10) if i%2 == 1] + 'X' )
    #summary_raw(['X'] )

