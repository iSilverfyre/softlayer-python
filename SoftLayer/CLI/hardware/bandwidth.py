"""Get details for a hardware device."""
# :license: MIT, see LICENSE for more details.

import click

import SoftLayer
from SoftLayer.CLI import environment
from SoftLayer.CLI import formatting
from SoftLayer.CLI import helpers
from SoftLayer import utils


@click.command()
@click.argument('identifier')
@click.option('--start_date', '-s', type=click.STRING, required=True,
              help="Start Date YYYY-MM-DD, YYYY-MM-DDTHH:mm:ss,")
@click.option('--end_date', '-e', type=click.STRING, required=True, 
              help="End Date YYYY-MM-DD, YYYY-MM-DDTHH:mm:ss")
@click.option('--summary_period', '-p', type=click.INT, default=3600, show_default=True,
              help="300, 600, 1800, 3600, 43200 or 86400 seconds")
@click.option('--quite_summary', '-q', is_flag=True, default=False, show_default=True,
              help="Only show the summary table")
@environment.pass_env
def cli(env, identifier, start_date, end_date, summary_period, quite_summary):
    """Bandwidth data over date range. Bandwidth is listed in GB
    
    Using just a date might get you times off by 1 hour, use T00:01 to get just the specific days data
    Timezones can also be included with the YYYY-MM-DDTHH:mm:ss.00000-HH:mm format.

    Example::

        slcli hw bandwidth 1234 -s 2019-05-01T00:01 -e 2019-05-02T00:00:01.00000-12:00
    """
    hardware = SoftLayer.HardwareManager(env.client)
    hardware_id = helpers.resolve_id(hardware.resolve_ids, identifier, 'hardware')
    data = hardware.get_bandwidth_data(hardware_id, start_date, end_date, None, summary_period)

    formatted_data = {}
    for point in data:
        key = utils.clean_time(point['dateTime'])
        data_type = point['type']
        value = round(point['counter'] / 2 ** 30,4)
        if formatted_data.get(key) is None:
            formatted_data[key] = {}
        formatted_data[key][data_type] = value

    table = formatting.Table(['Date', 'Pub In', 'Pub Out', 'Pri In', 'Pri Out'],
                             title="Bandwidth Report: %s - %s" % (start_date, end_date))

    sum_table = formatting.Table(['Type','Sum GB', 'Average MBps', 'Max GB', 'Max Date'], title="Summary")

    bw_totals = [
        {'keyName': 'publicIn_net_octet',   'sum': 0, 'max': 0, 'name': 'Pub In'},
        {'keyName': 'publicOut_net_octet',  'sum': 0, 'max': 0, 'name': 'Pub Out'},
        {'keyName': 'privateIn_net_octet',  'sum': 0, 'max': 0, 'name': 'Pri In'},
        {'keyName': 'privateOut_net_octet', 'sum': 0, 'max': 0, 'name': 'Pri Out'},
    ]
    for point in formatted_data:
        new_row = [point]
        for bw_type in bw_totals:
            counter = formatted_data[point].get(bw_type['keyName'], 0)
            new_row.append(mb_to_gb(counter))
            bw_type['sum'] = bw_type['sum'] + counter
            if counter > bw_type['max']:
                bw_type['max'] = counter
                bw_type['maxDate'] = point
        table.add_row(new_row)

    for bw_type in bw_totals:
        total = bw_type.get('sum', 0)
        average = 0
        if total > 0:
            average = round(total / len(formatted_data) / summary_period,4)
        sum_table.add_row([
            bw_type.get('name'),
            mb_to_gb(total),
            average,
            mb_to_gb(bw_type.get('max')),
            bw_type.get('maxDate')
        ])

    env.fout(sum_table)
    if not quite_summary:
        env.fout(table)


def mb_to_gb(x):
    return round(x / 2 ** 10, 4)