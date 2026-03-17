"""
InfluxDB Writer — Stores time-series metrics for the ML pipeline.
"""

import logging
from datetime import datetime
from typing import Dict, Optional

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

logger = logging.getLogger("metrics-collector.influx")


class InfluxWriter:
    """Writes metrics data points to InfluxDB 2.x."""

    def __init__(self, url: str, token: str, org: str, bucket: str):
        self.url = url
        self.org = org
        self.bucket = bucket
        self.client = InfluxDBClient(url=url, token=token, org=org)
        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
        self.query_api = self.client.query_api()
        logger.info("Connected to InfluxDB at %s (org=%s, bucket=%s)", url, org, bucket)

    def write_metrics(
        self,
        measurement: str,
        tags: Dict[str, str],
        fields: Dict[str, Optional[float]],
        timestamp: datetime,
    ):
        """Write a set of metric fields as a single data point."""
        # Filter out None values
        valid_fields = {k: v for k, v in fields.items() if v is not None}

        if not valid_fields:
            logger.warning("No valid fields to write, skipping.")
            return

        point = Point(measurement)
        for tag_key, tag_val in tags.items():
            point = point.tag(tag_key, tag_val)
        for field_key, field_val in valid_fields.items():
            point = point.field(field_key, float(field_val))
        point = point.time(timestamp, WritePrecision.S)

        try:
            self.write_api.write(bucket=self.bucket, record=point)
            logger.debug("Wrote %d fields to InfluxDB", len(valid_fields))
        except Exception as e:
            logger.error("Failed to write to InfluxDB: %s", e)

    def query_metrics(
        self,
        measurement: str,
        field: str,
        start: str = "-7d",
        stop: str = "now()",
        window: str = "1m",
    ) -> list:
        """
        Query historical metrics from InfluxDB.

        Returns list of dicts: [{"time": datetime, "value": float}, ...]
        """
        flux_query = f'''
        from(bucket: "{self.bucket}")
            |> range(start: {start}, stop: {stop})
            |> filter(fn: (r) => r._measurement == "{measurement}")
            |> filter(fn: (r) => r._field == "{field}")
            |> aggregateWindow(every: {window}, fn: mean, createEmpty: false)
            |> yield(name: "mean")
        '''

        try:
            result = self.query_api.query(flux_query, org=self.org)
            data = []
            for table in result:
                for record in table.records:
                    data.append({
                        "time": record.get_time(),
                        "value": record.get_value(),
                    })
            logger.debug("Queried %d data points from InfluxDB", len(data))
            return data
        except Exception as e:
            logger.error("Failed to query InfluxDB: %s", e)
            return []

    def close(self):
        """Close the InfluxDB connection."""
        self.client.close()
        logger.info("InfluxDB connection closed.")
