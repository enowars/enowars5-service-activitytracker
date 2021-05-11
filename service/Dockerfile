# Use a suitable base-image.
FROM rustlang/rust:nightly-buster

# Create our mapped data volume endpoint
RUN mkdir /data/

# Copy our service
COPY src/activitytracker/ /service/

# Change the working directory.
WORKDIR /service/
# Expose the service's port
EXPOSE 8000

ENV ROCKET_ADDRESS=0.0.0.0
ENV ROCKET_PORT=8000


RUN rustup default nightly
#RUN cargo install diesel_cli --no-default-features --features postgres
RUN apt-get update
RUN apt-get install libpq-dev -y
RUN cargo install diesel_cli --no-default-features --features postgres

COPY entrypoint.sh /
RUN chmod +x /entrypoint.sh

# Run the service
#ENTRYPOINT ["cargo", "run"]
ENTRYPOINT ["/entrypoint.sh"]