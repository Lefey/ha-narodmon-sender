# Narodmon Sender

This Home Assistant custom integration periodically sends values from selected sensors to [narodmon.ru](https://narodmon.ru).

## Installation

Copy the `custom_components/narodmon_sender` directory into your Home Assistant `custom_components` folder and restart Home Assistant.

## Configuration

1. In Home Assistant go to **Settings → Devices & Services**.
2. Add **Narodmon Sender** integration.
3. Enter your device ID and optional API key from narodmon.ru.
4. Choose sensors whose values should be sent and set the update interval.
5. Later, adjust the sensor list or interval from the integration's **Configure** options.

The integration will now push the chosen sensor states to narodmon.ru at the specified interval.
