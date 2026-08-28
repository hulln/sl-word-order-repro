# Corpus inputs

`inputs/` holds source material before thesis-specific preparation. No CoNLL-U
files are tracked in Git; obtain them under the paths below. Analysis scripts
read only the prepared paths listed in `config/corpora.tsv`.

| Input family | Official source | Expected input | Preparation and caveat | Licence |
|---|---|---|---|---|
| UD Slovenian-SSJ | [UD 2.18](https://github.com/UniversalDependencies/UD_Slovenian-SSJ/tree/r2.18) | `inputs/UD_Slovenian-SSJ` | Merge train, dev and test. | CC BY-SA 4.0 |
| UD Slovenian-SST | [UD 2.18](https://github.com/UniversalDependencies/UD_Slovenian-SST/tree/r2.18) | `inputs/UD_Slovenian-SST` | Merge the splits, then add CLASSLA 2.2.1 NER without changing syntax. | CC BY-SA 4.0 |
| SUK composite | [SUK 1.1](https://hdl.handle.net/11356/1959) | `inputs/combined_suk.conllu` | Split the supervisor-prepared composite into three genres. It is not a public download. | CC BY-SA 4.0 source; composite redistribution status unresolved |
| JANES News / Blog / Forum | [News](https://hdl.handle.net/11356/1140), [Blog](https://hdl.handle.net/11356/1138), [Forum](https://hdl.handle.net/11356/1139) | `inputs/janes.news.conllu`<br>`inputs/janes.blog.conllu`<br>`inputs/janes.forum.conllu` | Copy the supervisor-prepared CLASSLA UD conversions. Public releases are TEI/vertical. | CC BY 4.0 |
| JANES Tweet | [Tweet](https://hdl.handle.net/11356/1142) | `inputs/janes_tweet.conllu` | Copy the clean supervisor-prepared CLASSLA UD conversion. | CC BY-NC 4.0 |
| JANES-Wiki | [Janes-Wiki 1.0](https://hdl.handle.net/11356/1137) | `inputs/Janes-Wiki.vert.zip` | Historical route: vertical text to CLASSLA 2.2.1 UD/NER. The public package does not reproduce that conversion. | CC BY-SA 4.0 |
| CLASSLA-Wikipedia | [CLASSLA-Wikipedia 1.0](https://hdl.handle.net/11356/1427) | `inputs/classlawiki-sl.conllu.gz` | Decompress the distributed Slovenian CoNLL-U unchanged. | CC BY 4.0 |
| ParlaMint-SI | [ParlaMint.ana 4.0](https://hdl.handle.net/11356/1860) | `inputs/ParlaMint-SI.ana` | Concatenate all distributed CoNLL-U files in lexicographically sorted full-path order. | CC BY 4.0 |
| KDSP | [KDSP 1.0](https://hdl.handle.net/11356/1823) | `inputs/KDSP.txt` | Historical route: annotate the 262 public texts with CLASSLA 2.2.1. This route is not runnable here. | CC BY 4.0 |
| AI-GenT supplementary comparison sets | [AI-GenT 1.0](https://hdl.handle.net/11356/2210) | `inputs/aigent-gpt5.conllu`<br>`inputs/aigent-gams27b.conllu`<br>`inputs/aigent-gemma2-27b.conllu` | Copy the distributed Slovenian `4y-gs`, default-prompt GPT-5, GaMS-27B and gemma-2-27b files unchanged. These are distinct from the matched `4y-ss` GPT-5 essays. | CC BY-NC-SA 4.0 |
| Matched human essays | [Šolar 3.0](https://hdl.handle.net/11356/1589) | `inputs/human-essays.conllu` | Use the 691 fourth-year secondary-school essays corresponding to the human side of AI-GenT's `4y-ss` setup. Syntax is automatic, but its annotator is undocumented; add CLASSLA 2.2.1 NER without changing syntax. The derived annotated Human subset is not distributed in this repository and must be obtained or prepared from the source data. | CC BY-NC-SA 4.0 |
| Matched GPT-5 essays | [AI-GenT 1.0](https://hdl.handle.net/11356/2210) | `inputs/gpt5-essays.conllu` | Normalize the Slovenian `Solar/4y-ss/GPT-5/pap` cell by blanking DEPS and MISC, then add CLASSLA 2.2.1 standard NER in pretokenized mode. Syntax remains Trankit (UD v2.15 model). | CC BY-NC-SA 4.0 |

## SUK

The thesis used a supervisor-prepared SUK composite that is wider than the
public CoNLL-U release. The literary, publicistic and professional analysis
files all derive from that composite and cannot be rebuilt from the public
release. On the material that could be compared with SUK 1.1, the fields used by
the word-order query (`FORM`, `UPOS`, `HEAD`, `DEPREL`) matched.

## Matched human and GPT-5 essays

The thesis pair contains 691 matched fourth-year secondary-school documents.
The GPT-5 side is AI-GenT 1.0's `sl/Solar/4y-ss/GPT-5/pap` cell; the human side
is the same Šolar subset. GPT-5 syntax comes from AI-GenT's Trankit annotation.
The human syntactic annotator is undocumented.

Neither base input contains NER. The GPT-5 base is the AI-GenT cell with DEPS and
MISC set to `_`, removing `SpaceAfter=No`; its verified SHA-256 is
`a9945c5d40f9e7f6a066da2d2c549c76a26ca6d20b4bd7ff01b49e80e2e247a0`.
`scripts/prepare_corpora.py` adds CLASSLA 2.2.1 standard NER in pretokenized mode
using [model 11356/2014/ner](https://hdl.handle.net/11356/2014/ner) to an already
normalized base file; it does not reproduce the upstream normalization itself.

The resulting canonical GPT-5 prepared SHA-256 is
`bb2b43f91d72c647583813e665f2ef3152acaab71880f5f73afc7642cd191669`.
Both essay reconstructions preserve columns 1–9 and reproduce all cached thesis
NER counts, but they are not claimed to be byte-identical to the lost historical
NER-enriched derivatives. The derived annotated Human subset is not distributed
in this repository and must be obtained or prepared from the source data.

## AI-GenT supplementary comparison sets

The three `4y-gs`, default-prompt files compare GPT-5, GaMS-27B and
gemma-2-27b. They are not the same generated texts as the matched `4y-ss`,
`GPT-5/pap` set. The `4y-gs` GPT-5 subset uses 205 source documents that are
also among the matched 691, so this is a supplementary model/prompt comparison,
not an independent replication.
