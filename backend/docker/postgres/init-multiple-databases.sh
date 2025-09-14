#!/bin/bash
set -e

IFS=',' read -r -a databases <<< "$POSTGRES_MULTIPLE_DATABASES"
IFS=',' read -r -a users <<< "$POSTGRES_MULTIPLE_USERS"
IFS=',' read -r -a passwords <<< "$POSTGRES_MULTIPLE_PASSWORDS"

if [ ${#databases[@]} -ne ${#users[@]} ] || [ ${#databases[@]} -ne ${#passwords[@]} ]; then
    echo "Error: Number of databases, users, and passwords must match"
    exit 1
fi

for i in "${!databases[@]}"; do
    DB="${databases[$i]}"
    USER="${users[$i]}"
    PASS="${passwords[$i]}"
    
    echo "Creating database '$DB' with user '$USER'"
    
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
        CREATE USER "$USER" WITH PASSWORD '$PASS';
        CREATE DATABASE "$DB" WITH OWNER "$USER" ENCODING 'UTF8';
        GRANT ALL PRIVILEGES ON DATABASE "$DB" TO "$USER";
EOSQL

    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$DB" <<-EOSQL
        GRANT ALL ON SCHEMA public TO "$USER";
EOSQL
done

echo "Multiple databases and users created successfully"
