# Use a suitable base-image.
FROM liuchong/rustup

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
RUN cargo build

# Run the service
ENTRYPOINT ["cargo", "run"]
