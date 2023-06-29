from google.cloud import dataplex_v1
from google.cloud import bigquery
from google.oauth2 import service_account
import argparse
import time
from google.protobuf.json_format import MessageToJson


parser = argparse.ArgumentParser()
parser.add_argument('--key_loc', '-key', help='Path to the key for the service account json')
parser.add_argument('--datascan_name', '-dsn', help='Full project path of the Datascan')
parser.add_argument('--dataset', '-dst', help='Full Dataset ID: project.dataset')
parser.add_argument('--table', '-tbl', help='Base table name to create for DQ results. This will be created as `table_per_job`')
parser.add_argument('--dataset_location', '-loc', help='Location of your dataset, e.g. us-central1')

args = parser.parse_args()

def export_data():
    # replace Service Account keys with your .json credentials
    key_path = args.key_loc
    credentials = service_account.Credentials.from_service_account_file(
        key_path, scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    bq_client = bigquery.Client(
        credentials=credentials, project=credentials.project_id,)

    dataset = bigquery.Dataset(
        dataset_ref=args.dataset
    )
    dataset.location = args.dataset_location
    bq_client.create_dataset(dataset=dataset, exists_ok=True)

    schema_per_job = [
        bigquery.SchemaField(name="datascan_id", field_type="STRING"),
        bigquery.SchemaField(name="table_id", field_type="STRING"),
        bigquery.SchemaField(name="job_id", field_type="STRING"),
        bigquery.SchemaField(name="records_scannned", field_type="INT64"),
        bigquery.SchemaField(name="passed", field_type="BOOLEAN"),
        bigquery.SchemaField(name="total_rules", field_type="INT64"),
        bigquery.SchemaField(name="passing_rules", field_type="INT64"),
        bigquery.SchemaField(name="job_start_time", field_type="TIMESTAMP"),
        bigquery.SchemaField(name="job_end_time", field_type="TIMESTAMP"),
        bigquery.SchemaField(name="scanned_data", field_type="JSON"),
        bigquery.SchemaField(name="rule_results", field_type="JSON"),
    ]

    schema_per_rule = [
        bigquery.SchemaField(name="job_name", field_type="STRING"),
        bigquery.SchemaField(name="datascan", field_type="STRING"),
        bigquery.SchemaField(name="job", field_type="STRING"),
        bigquery.SchemaField(name="rule_config", field_type="JSON"),
        bigquery.SchemaField(name="dimension", field_type="STRING"),
        bigquery.SchemaField(name="passed", field_type="BOOLEAN"),
        bigquery.SchemaField(name="pass_ratio", field_type="FLOAT"),
        bigquery.SchemaField(name="debug_query", field_type="STRING"),
    ]

    table_per_job = bigquery.Table(
        table_ref=args.dataset + "." + args.table + "_per_job",
        schema=schema_per_job,
    )
    bq_client.create_table(table=table_per_job, exists_ok=True)

    table_per_rule = bigquery.Table(
        table_ref=args.dataset + "." + args.table + "_per_rule",
        schema=schema_per_rule,
    )
    bq_client.create_table(table=table_per_rule, exists_ok=True)

    # Get Jobs Data
    print("Getting DQ Jobs Data")
    client = dataplex_v1.DataScanServiceClient(credentials=credentials,)

    request_scan = dataplex_v1.GetDataScanRequest(name=args.datascan_name)
    response_scan = client.get_data_scan(request=request_scan)

    request = dataplex_v1.ListDataScanJobsRequest(
        parent=args.datascan_name, page_size=10)

    page_result = client.list_data_scan_jobs(request=request)
    counter = 0
    job_names = []
    for response in page_result:
        counter += 1
        job_names.append(response.name)
        # Limit to only 5 jobs by uncommenting below
        # if counter == 5:
        #   break
        if counter % 60 == 0:
            time.sleep(30)
            # break
            print("Waiting 30 seconds before fetching more jobs")

    print('Jobs scanned: ' + str(counter))
    print(*job_names, sep="\n")

    # Write Jobs data to bigquery
    print("Writing Jobs data to bigquery:")
    for job_name in job_names:
        print(job_name)
        job_request = dataplex_v1.GetDataScanJobRequest(
            name=job_name,
            view="FULL",
        )
        job_result = client.get_data_scan_job(request=job_request)
        # Skips jobs if not in succeeded state
        if job_result.state != 4:
            continue

        split_job = job_result.name.split("/")
        passing_rules = 0
        failing_rules = 0
        for rule in job_result.data_quality_result.rules:
            if rule.passed is True:
                passing_rules += 1
            elif rule.passed is False:
                failing_rules += 1
        print(' -->Passing rules = ' + str(passing_rules))
        print(' -->Failing rules = ' + str(failing_rules))

        bq_client.insert_rows(
            table=args.dataset + "." + args.table + "_per_job",
            rows=[(
                split_job[1] + "/" + split_job[5],
                response_scan.data.entity,
                job_result.uid,
                job_result.data_quality_result.row_count,
                job_result.data_quality_result.passed,
                len(job_result.data_quality_result.rules),
                passing_rules,
                job_result.start_time,
                job_result.end_time,
                MessageToJson(job_result.data_quality_result.scanned_data._pb),
                MessageToJson(job_result.data_quality_result._pb),
            )],
            selected_fields=schema_per_job,
        )

        for rule_result in job_result.data_quality_result.rules:
            bq_client.insert_rows(
                table=args.dataset + "." + args.table + "_per_rule",
                rows=[(
                    job_result.name,
                    split_job[5],
                    split_job[7],
                    MessageToJson(rule_result.rule._pb),
                    rule_result.rule.dimension,
                    rule_result.passed,
                    rule_result.pass_ratio,
                    rule_result.failing_rows_query
                )],
                selected_fields=schema_per_rule,
            )


export_data()

