use diesel::pg::PgConnection;
use r2d2;
use diesel::r2d2::ConnectionManager;
use rocket::http::Status;
use rocket::request::{FromRequest, Outcome, Request};
use rocket::State;
use std::ops::Deref;
use serde::{Serialize, Deserialize};
use std::fmt;
use std::sync::Arc;
use scheduled_thread_pool;


#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct DbConfig {
    pub host: String,
    pub port: u16,
    pub user: String,
    pub password: String,
    pub database: String,
}

impl fmt::Display for DbConfig {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        let connect = format!("postgres://{}:{}@{}:{}/{}", self.user, self.password, self.host, self.port, self.database);
        write!(f, "{}", connect)
    }
}

pub type Pool = r2d2::Pool<ConnectionManager<PgConnection>>;

pub fn init_pool(config: DbConfig) -> Pool {
    let manager = ConnectionManager::<PgConnection>::new(config.to_string());
    r2d2::Pool::builder()
        .max_size(1024)
        .thread_pool(Arc::from(scheduled_thread_pool::ScheduledThreadPool::new(1024)))
        .build(manager)
        .expect("Could not create db pool")
}

pub struct DbConn(pub r2d2::PooledConnection<ConnectionManager<PgConnection>>);

#[rocket::async_trait]
impl<'r> FromRequest<'r> for DbConn {
    type Error = ();

    async fn from_request(request: &'r Request<'_>) -> Outcome<Self, Self::Error> {
        let pool = request.guard::<&State<Pool>>().await.succeeded().unwrap();
        let mut tries = 0;
        while tries < 10 {
            match pool.get() {
                Ok(conn) => return Outcome::Success(DbConn(conn)),
                Err(_) => (),
            }
            tries += 1;
        }
        Outcome::Failure((Status::ServiceUnavailable, ()))
    }
}

impl Deref for DbConn {
    type Target = PgConnection;

    fn deref(&self) -> &Self::Target {
        &self.0
    }
}