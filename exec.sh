#!/bin/bash

# Default values
key_loc=""
data_set=""
data_scan=""
table=""
data_set_loc=""


# Function to display the usage of the script
usage() {
    echo "Usage: $0 --key-loc <value> --data-set <value> --data-scan <value> --table <value> --data-set-loc <value>"
    echo "Options:"
    echo "  --key-loc        Specify service account key location"
    echo "  --data-set       Specify dataset for data quality job"
    echo "  --data-scan      Specify path to the datascan job"
    echo "  --table          Specify table for results"
    echo "  --data-set-loc   Specify location of the dataset"
    
}

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        \-\-key-loc)
            key_loc="$2"
            shift
            shift
            ;;
        \-\-data-set)
            data_set="$2"
            shift
            shift
            ;;
        \-\-data-scan)
            data_scan="$2"
            shift
            shift
            ;;
        \-\-table)
            table="$2"
            shift
            shift
            ;;
        \-\-data-set-loc)
            data_set_loc="$2"
            shift
            shift
            ;;
        *)
            echo "Invalid argument: $1"
            usage
            exit 1
            ;;
    esac
done

# Validate the required parameters

if [[ -z $key_loc ]]; then
    echo "Missing required parameter: --key-loc"
    usage
    exit 1
fi

if [[ -z $data_set ]]; then
    echo "Missing required parameter: --data-set"
    usage
    exit 1
fi

if [[ -z $data_scan ]]; then
    echo "Missing required parameter: --data-scan"
    usage
    exit 1
fi

if [[ -z $table ]]; then
    echo "Missing required parameter: --table"
    usage
    exit 1
fi

if [[ -z $data_set_loc ]]; then
    echo "Missing required parameter: --data-set-loc"
    usage
    exit 1
fi

# Execute the Python script with the named parameters

echo "Installing dependency: pip install google-cloud-dataplex"
pip install google-cloud-dataplex > /dev/null 2>&1
echo "Installing dependency: pip install google-cloud-bigquery"
pip install google-cloud-bigquery > /dev/null 2>&1

echo --key_loc "$key_loc" --datascan "$data_scan" --dataset "$data_set" --table "$table" --dataset_location "$data_set_loc"
python dataplex_autodq_export_bq.py --key_loc "$key_loc" --datascan "$data_scan" --dataset "$data_set" --table "$table" --dataset_location "$data_set_loc"

