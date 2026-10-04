# Article V, Measured in People

Code and data for a working paper by Timothy J. Miano that restates Article V's three-quarters ratification rule, and every ratification since 1788, in population and state legislators.

- Site: https://articlevmeasured.pages.dev (overview, fact sheet, methods and limitations)
- Estate of Bits post: https://estateofbits.substack.com/p/article-v-measured-in-people

Working paper; not peer reviewed.

## Status of the data

**Ratification dates are provisional.** `data/ledger.csv` (1,013 state ratifications, rejections, and rescissions) is built from `data/ratifications_*.csv`. Founding-era rows cite the U.S. Senate Manual on GovInfo; most later rows cite secondary compilations and are being re-sourced to primary records (state journals, the Congressional Record, archival notices). Threshold shares, final shares, and counts of rejections and rescissions may change. The ratification and blocking floors use only census populations (`population.csv`) and admission dates (`states.csv`).

Every data row carries the URL of its source in `source_url`. Convention-application data and congressional roll calls are not part of this release. The actors directory (`actors/`) is a separate research collection with its own data dictionary, methods and corrections process; see `actors/README.md`.

## Layout

```
data/                    inputs, one source URL per row
engine/model.py          metrics (floors, threshold and final shares, coalition distributions)
engine/specgrid.py       specification curve (24 combinations of data-handling choices)
engine/report.py         writes out/ series
engine/build.py          validates the ratification tables and rebuilds data/ledger.csv
engine/tests/            synthetic-fixture tests; the arithmetic is checked independently of the real data
factsheet-build/         fact sheet numbers (build_data.py, then fix.py and fix2.py -> facts.json) and print figures (gdoc/figures.py)
actors/                  Article V Actors Directory: public export (actors_public.csv), data dictionary and methods,
                         corrections process, change log, and the findings charts (figures/)
```

## Reproduce

Requires [uv](https://docs.astral.sh/uv/). From the repository root:

```sh
uv run pytest engine/tests
uv run python -m engine.report
uv run python -m engine.specgrid   # slow: several minutes
PYTHONPATH=. uv run python factsheet-build/build_data.py
PYTHONPATH=. uv run python factsheet-build/fix.py
PYTHONPATH=. uv run python factsheet-build/fix2.py
uv run python factsheet-build/gdoc/figures.py
```

## Prior work

This work reproduces and extends Peter Suber, *Population Changes and Constitutional Amendments: Federalism versus Democracy*, 20 U. Mich. J.L. Reform 409 (1987). Using his convention, it matches 36 of his 40 published values to within 0.1 point.

## Corrections

Reply to the [Estate of Bits post](https://estateofbits.substack.com/p/article-v-measured-in-people) or open an issue here, with the item and a source.

## Cite

Timothy J. Miano, *Article V, Measured in People* (working paper, 2026), https://articlevmeasured.pages.dev/.

## License

- **Code** (`engine/`, `factsheet-build/`): MIT. See `LICENSE`.
- **Tables adapted in part from Wikipedia:** CC BY-SA 4.0, see `LICENSE-CC-BY-SA-4.0.txt`, with attribution in `NOTICE-WIKIPEDIA.md`. These are `data/ledger.csv`, `population.csv`, `ratifications_01_13.csv`, `ratifications_14_27.csv`, `ratifications_unratified.csv`, `states.csv`, `votes_cast.csv`, `boundaries.csv`, `legislature_sizes.csv`, `ratification_margins.csv`, `secession.csv` and `amendments_meta.csv`. Rows taken from Wikipedia cite the article in `source_url`.
- **Other data, the actors directory (`actors/`), text and figures:** CC BY 4.0. See `LICENSE-CC-BY-4.0.txt`.

Underlying facts come from the cited sources, whose own terms apply to material taken directly from them.
