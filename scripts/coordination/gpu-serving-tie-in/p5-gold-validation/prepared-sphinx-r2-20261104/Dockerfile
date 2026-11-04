FROM swebench/sweb.eval.x86_64.sphinx-doc_1776_sphinx-8593@sha256:bf09a4f64ca8a2dd3c9e2d252d640ed0239e6b2927fa524e40b6cde7aa0fafc0
ENV PIP_NO_INDEX=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN bash -lc 'source /opt/miniconda3/bin/activate testbed && cd /testbed && git reset --hard 07983a5a8704ad91ae855218ecbda1c8598200ca && git clean -ffdx && python -m pip install --no-index --no-build-isolation --no-deps -e ".[test]" && python -m pip check && python -c "import sphinx, pytest, tox; print(sphinx.__version__)"'
