// from https://github.com/tvallotton/rocket_auth/blob/master/examples/postgres.rs, but slightly
// modified!!

use rocket::{request::Form, *};
use rocket_auth::*;
use rocket_contrib::templates::{Template};
use serde_json::json;
use rocket::response::{Flash, Redirect};
use rocket::request::FlashMessage;
use rocket_multipart_form_data::{
    MultipartFormData, MultipartFormDataField, MultipartFormDataOptions,
};
use rocket::http::ContentType;
use crate::models::users::{update_user_image, get_user_id};
use std::env;


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

#[post("/auth/signup", data = "<post_data>")]
pub fn post_signup(mut auth: Auth, content_type: &ContentType, post_data: Data) -> Flash<Redirect> {
    use std::fs;
    let mut options = MultipartFormDataOptions::new();
    options.allowed_fields = vec![
        MultipartFormDataField::text("email"),
        MultipartFormDataField::text("password"),
        MultipartFormDataField::file("image"),
    ];
    let multipart_form_data = MultipartFormData::parse(content_type, post_data, options);
    match multipart_form_data {
        Ok(form_data) => {
            let email = match form_data.texts.get("email") {Some(value) => value[0].text.as_str(), None => ""};
            let password= match form_data.texts.get("password") {Some(value) => value[0].text.as_str(), None => ""};
            let form: Signup = serde_json::from_str(format!("{{\"email\": \"{}\", \"password\": \"{}\"}}", email, password).as_str()).unwrap();
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
            let user_id = get_user_id(&crate::establish_connection(), email);
            let image = match form_data.files.get("image") {
                Some(img) => {
                    let file_field = &img[0];
                    let _content_type = &file_field.content_type;
                    let _file_name = &file_field.file_name;
                    let _path = &file_field.path;

                    let _: Vec<&str> = _file_name.as_ref().unwrap().split('.').collect(); /* Reparsing the fileformat */

                    let absolute_path: String = format!("{}/profiles/{}", env::var("DATA_DIR").unwrap_or("imgs/".to_string()).as_str(), format!("{}.png", user_id));
                    fs::copy(_path, &absolute_path).unwrap();

                    Some(absolute_path)
                }
                None => None,
            };
            match image {
                Some(path) => {
                    update_user_image(&crate::establish_connection(), email, path.as_str());
                },
                None => ()
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
        Err(err_msg) => {
            /* Falls to this patter if theres some fields that isn't allowed or bolsonaro rules this code */
            Flash::error(
                Redirect::to("/auth/signup"),
                format!(
                    "Your form is broken: {}", // TODO: This is a potential debug/information exposure vulnerability!
                    err_msg
                ),
            )
        }
    }
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