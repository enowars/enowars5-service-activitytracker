// from https://github.com/tvallotton/rocket_auth/blob/master/examples/postgres.rs, but slightly
// modified!!

use rocket::{request::Form, *};
use rocket_auth::*;
use rocket_contrib::templates::{Template};
use serde_json::json;
use rocket::response::{Flash, Redirect};
use rocket::request::FlashMessage;


#[get("/auth/login")]
pub fn get_login(flash: Option<FlashMessage>) -> Template {
    if let Some(ref msg) = flash {
        Template::render("auth/login", json!({
            "flash": msg.msg()
        }))
    } else {
        Template::render("auth/login", json!({}))
    }
}

#[post("/auth/login", data = "<form>")]
pub fn post_login(mut auth: Auth, form: Form<Login>) -> Flash<Redirect> {
    let res = auth.login(&form).map_err(|x|x.message(Language::EN));
    match res {
        Ok(()) => Flash::success(
            Redirect::to("/posts"),
            "Logged in!",
        ),
        Err(e) => Flash::error(
            Redirect::to("/auth/login"),
            format!(
                "Error creating user: {}",
                e.to_string()
            )
        )
    }
}

#[get("/auth/signup")]
pub fn get_signup(flash: Option<FlashMessage>) -> Template {
    if let Some(ref msg) = flash {
        Template::render("auth/signup", json!({
            "flash": msg.msg()
        }))
    } else {
        Template::render("auth/signup", json!({}))
    }
}

#[post("/auth/signup", data = "<form>")]
pub fn post_signup(mut auth: Auth, form: Form<Signup>) -> Flash<Redirect> {
    match auth.signup(&form) {
        Err(e) => return Flash::error(
            Redirect::to("/auth/signup"),
            format!(
                "Error creating user: {}",
                e.to_string()
            ),
        ),
        _ => ()
    };
    match auth.login(&form.into()) {
        Err(e) => return Flash::error(
            Redirect::to("/auth/login"),
            format!(
                "User created but error logging in: {}",
                e.to_string()
            ),
        ),
        _ => ()
    };
    Flash::success(
        Redirect::to("/posts"),
        "Logged in!",
    )
}

#[get("/auth/logout")]
pub fn logout(mut auth: Auth) -> Result<Redirect, String> {
    auth.logout().expect("Could not log out!");
    Ok(Redirect::to("/"))
}
#[get("/auth/delete")]
pub fn delete(mut auth: Auth) -> Result<Redirect, String> {
    auth.delete().expect("Could not delete post!");
    Ok(Redirect::to("/"))
}