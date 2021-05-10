import attr
from pathlib import Path

from pylexibank import Concept, Language
from pylexibank.dataset import Dataset as BaseDataset
from pylexibank.util import progressbar


from cldfbench import CLDFSpec
from csvw import Datatype
from pyclts import CLTS
from pycldf.terms import Terms


import lingpy
from clldutils.misc import slug
from unicodedata import normalize


@attr.s
class CustomConcept(Concept):
    Chinese_Gloss = attr.ib(default=None)
    Number = attr.ib(default=None)


@attr.s
class CustomLanguage(Language):
    Latitude = attr.ib(default=None)
    Longitude = attr.ib(default=None)
    SubGroup = attr.ib(default=None)
    Name_in_Source = attr.ib(default=None)
    Location = attr.ib(default=None)


class Dataset(BaseDataset):
    dir = Path(__file__).parent
    id = "zhoubizic"
    concept_class = CustomConcept
    language_class = CustomLanguage

    def cmd_download(self, **kw):
        self.raw_dir.write("sources.bib", getEvoBibAsBibtex("Allen2007", **kw))

    def cldf_specs(self):
        return {
            None: BaseDataset.cldf_specs(self),
            'structure': CLDFSpec(
                module='StructureDataset',
                dir=self.cldf_dir,
                data_fnames={'ParameterTable': 'features.csv'}
            )
        }

    def cmd_makecldf(self, args):

        with self.cldf_writer(args) as writer:
            wl = lingpy.Wordlist(self.raw_dir.joinpath("wordlist.tsv").as_posix())
            writer.add_sources()

            # TODO: add concepts with `add_concepts`
            concepts = {}
            for concept in self.concepts:
                idx = concept['NUMBER']+ '_'+slug(concept['ENGLISH'])
                writer.add_concept(
                    ID=idx,
                    Name=concept['ENGLISH'],
                    Chinese_Gloss=concept["CHINESE"],
                    Number=concept['NUMBER'],
                    #Concepticon_ID=concept.concepticon_id,
                    #Concepticon_Gloss=concept.concepticon_gloss,
                )
                concepts[concept["ENGLISH"]] = idx
            languages = writer.add_languages(lookup_factory="Name_in_Source")
            wl.renumber("cog")
            for k in progressbar(wl, desc="wl-to-cldf"):
                if wl[k, "value"]:
                    lexeme = writer.add_form(
                        Language_ID=languages[wl[k, "doculect"]],
                        Parameter_ID=concepts[wl[k, "concept"]],
                        Value=wl[k, "value"],
                        Form=self.lexemes.get(wl[k, "form"], wl[k, "form"]),
                        Source="Allen2007",
                    )
                    #writer.add_cognate(
                    #        lexeme=lexeme,
                    #        Cognateset_ID=wl[k, "cogid"],
                    #        Source=["Zhou2020"]
                    #        )
            language_table = writer.cldf['LanguageTable']

        with self.cldf_writer(args, cldf_spec='structure', clean=False) as writer:
            cltstable = Terms()["cltsReference"].to_column().asdict()

            # We share the language table across both CLDF datasets:
            writer.cldf.add_component(language_table)
            writer.objects['LanguageTable'] = self.languages
            inventories = self.raw_dir.read_csv(
                'inventories.tsv', normalize='NFC', delimiter='\t', dicts=True)

            writer.cldf.add_columns(
                    'ParameterTable',
                    cltstable,
                    {'name': 'CLTS_BIPA', 'datatype': 'string'},
                    {'name': 'CLTS_Name', 'datatype': 'string'},
                    {
                        'name': 'Lexibank_BIPA',
                        'datatype': 'string',
                    },
                    {
                        'name': "Prosody",
                        "datatype": "string"
                    }
                    )
            writer.cldf.add_columns(
                    'ValueTable',
                    {'name': 'Context', 'datatype': 'string'}
                    )

            clts = CLTS(args.clts.dir)
            bipa = clts.transcriptionsystem_dict['bipa']
            #td = clts.transcriptiondata_dict['zhoubizic']
            pids, visited = {}, set()
            for row in progressbar(inventories, desc='inventories'):
                for s1, s2, p in zip(
                        row['Value'].split(),
                        row['Lexibank'].split(),
                        row['Prosody'].split()
                        ):
                    pidx = '-'.join([
                        str(hex(ord(s)))[2:].rjust(4, '0') for s in
                        row['Value']])+'_'+p
                    s1 = normalize("NFD", s1)
                    #if not s1 in td.grapheme_map:
                    #    args.log.warn('missing sound {0} / {1}'.format(
                    #        s1, ' '.join([str(hex(ord(x))) for x in s1])))
                    #else:
                    sound = bipa[s2]
                    sound_name = sound.name if sound.type not in [
                        'unknown', 'marker'] else ''
                    if not pidx in visited:
                        visited.add(pidx)
                        writer.objects['ParameterTable'].append({
                            'ID': pidx,
                            'Name': s1,
                            'Description': sound_name,
                            'CLTS_BIPA': sound.s,
                            'CLTS_Name': sound_name,
                            'Lexibank_BIPA': s2,
                            'Prosody': p,
                            })
                    writer.objects['ValueTable'].append({
                        'ID': row['Language_ID']+'_'+pidx,
                        'Language_ID': row['Language_ID'],
                        'Parameter_ID': pidx,
                        'Value': s1,
                        'Context': p,
                        'Source': ['Zhou2021'],
                        })
