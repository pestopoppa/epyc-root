FROM sha256:9b1cabf7bcd83a28469f67e3852d8e2207e90d45aa71f436bb7e600bdee8bae2
COPY wheelhouse/ /p5-offline-wheelhouse/
COPY WHEELHOUSE.sha256 /p5-wheelhouse.sha256
COPY requirements.txt /p5-requirements.txt
RUN cd /p5-offline-wheelhouse && sha256sum -c /p5-wheelhouse.sha256 && \
    bash -lc 'source /opt/miniconda3/bin/activate testbed && cd /testbed && git reset --hard d16bfe05a744909de4b27f5875fe0d4ed41ce607 && git clean -ffdx && export PIP_NO_INDEX=1 PIP_FIND_LINKS=/p5-offline-wheelhouse PIP_DISABLE_PIP_VERSION_CHECK=1 && python -m pip install --no-index --find-links=/p5-offline-wheelhouse -r /p5-requirements.txt && python -m pip install --no-index --find-links=/p5-offline-wheelhouse --no-build-isolation -e ".[test]" && python -m pip check && python -c "import astropy, pytest, numpy; print(astropy.__version__, astropy.__file__, pytest.__version__, numpy.__version__)"'
