from pathlib import Path
from unicodedata import normalize

import attr
import lingpy
from cldfbench import CLDFSpec
from clldutils.misc import slug
from pycldf.terms import Terms
from pyclts import CLTS
from pylexibank import Concept, Language
from pylexibank.dataset import Dataset as BaseDataset
from pylexibank.util import progressbar


@attr.s
class CustomCognate(Concept):
    Morpheme_Index = attr.ib(default=None)


@attr.s
class CustomConcept(Concept):
    Chinese_Gloss = attr.ib(default=None)
    Number = attr.ib(default=None)


@attr.s
class CustomLanguage(Language):
    SubGroup = attr.ib(default=None)
    Name_in_Source = attr.ib(default=None)
    Location = attr.ib(default=None)


class Dataset(BaseDataset):
    dir = Path(__file__).parent
    id = "zhoubizic"
    writer_options = dict(keep_languages=False, keep_parameters=False)

    concept_class = CustomConcept
    language_class = CustomLanguage

    def cmd_download(self, **kw):
        pass

    def cldf_specs(self):
        return {
            None: BaseDataset.cldf_specs(self),
            "structure": CLDFSpec(
                module="StructureDataset",
                dir=self.cldf_dir,
                data_fnames={"ParameterTable": "features.csv"},
            ),
        }

    def cmd_makecldf(self, args):
        with self.cldf_writer(args) as writer:
            wl = lingpy.Wordlist(self.raw_dir.joinpath("wordlist.tsv").as_posix())
            writer.add_sources()

            concept_lookup = {}
            for concept in self.conceptlists[0].concepts.values():
                idx = concept.id.split("-")[-1] + "_" + slug(concept.english)
                concept_lookup[concept.english] = idx
                writer.add_concept(
                    ID=idx,
                    Concepticon_ID=concept.concepticon_id,
                    Concepticon_Gloss=concept.concepticon_gloss,
                    Name=concept.english,
                    Number=concept.number,
                    Chinese_Gloss=concept.attributes["chinese"],
                )

            languages = writer.add_languages(lookup_factory="Name_in_Source")
            for k in progressbar(wl, desc="wl-to-cldf"):
                if wl[k, "value"]:
                    lex = writer.add_form(
                        Language_ID=languages[wl[k, "doculect"]],
                        Parameter_ID=concept_lookup[wl[k, "concept"]],
                        Value=wl[k, "value"],
                        Cognacy=wl[k, "cog"],
                        Form=self.lexemes.get(wl[k, "form"], wl[k, "form"]),
                        Source="Zhou2020",
                    )

            language_table = writer.cldf["LanguageTable"]

        with self.cldf_writer(args, cldf_spec="structure", clean=False) as writer:
            cltstable = Terms()["cltsReference"].to_column().asdict()

            # We share the language table across both CLDF datasets:
            writer.cldf.add_component(language_table)
            inventories = self.raw_dir.read_csv(
                "inventories.tsv", normalize="NFC", delimiter="\t", dicts=True
            )

            writer.cldf.add_columns(
                "ParameterTable",
                cltstable,
                {"name": "CLTS_BIPA", "datatype": "string"},
                {"name": "CLTS_Name", "datatype": "string"},
                {"name": "Lexibank_BIPA", "datatype": "string"},
                {"name": "Prosody", "datatype": "string"},
            )
            writer.cldf.add_columns("ValueTable", {"name": "Context", "datatype": "string"})

            clts = CLTS(args.clts.dir)
            bipa = clts.transcriptionsystem_dict["bipa"]
            pids, visited = {}, set()
            for row in progressbar(inventories, desc="inventories"):
                for s1, s2, p in zip(
                    row["Value"].split(), row["Lexibank"].split(), row["Prosody"].split()
                ):
                    pidx = (
                        "-".join([str(hex(ord(s)))[2:].rjust(4, "0") for s in row["Value"]])
                        + "_"
                        + p
                    )
                    s1 = normalize("NFD", s1)
                    sound = bipa[s2]
                    sound_name = sound.name if sound.type not in ["unknown", "marker"] else ""
                    if not pidx in visited:
                        visited.add(pidx)
                        writer.objects["ParameterTable"].append(
                            {
                                "ID": pidx,
                                "Name": s1,
                                "Description": sound_name,
                                "CLTS_BIPA": sound.s,
                                "CLTS_Name": sound_name,
                                "Lexibank_BIPA": s2,
                                "Prosody": p,
                            }
                        )
                    writer.objects["ValueTable"].append(
                        {
                            "ID": row["Language_ID"] + "_" + pidx,
                            "Language_ID": row["Language_ID"],
                            "Parameter_ID": pidx,
                            "Value": s1,
                            "Context": p,
                            "Source": ["Zhou2021"],
                        }
                    )
