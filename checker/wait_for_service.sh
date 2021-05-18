until nc -vz -w 100 postgres 5432
do
  sleep 1
done

sleep 30