#!/bin/bash
uv run pytest --cov=silvasonic_birdnet containers/birdnet/tests --cov-report term-missing > birdnet_cov.txt 2>&1
uv run pytest --cov=silvasonic_healthchecker containers/healthchecker/tests --cov-report term-missing > healthchecker_cov.txt 2>&1
uv run pytest --cov=silvasonic_livesound containers/livesound/tests --cov-report term-missing > livesound_cov.txt 2>&1
uv run pytest --cov=silvasonic_recorder containers/recorder/tests --cov-report term-missing > recorder_cov.txt 2>&1
uv run pytest --cov=silvasonic_uploader containers/uploader/tests --cov-report term-missing > uploader_cov.txt 2>&1
uv run pytest --cov=silvasonic_weather containers/weather/tests --cov-report term-missing > weather_cov.txt 2>&1
echo "Done"
