use rocket_contrib::templates::Template;

use rocket::request::FlashMessage;
use rocket::response::{Flash, Redirect};

use rocket::http::ContentType;
use rocket::Data;
use rocket_multipart_form_data::{MultipartFormData, MultipartFormDataField, MultipartFormDataOptions};
use rocket_auth::User;
use serde_json::json;
use crate::models::users::get_user_id;
use crate::models::friends::create_friend;


#[get("/friends")]
pub fn new(user: User, flash: Option<FlashMessage>) -> Template {
    let (m_name, m_msg) = match flash {
        Some(ref msg) => (msg.name(), msg.msg()),
        None => ("success", "Add a friend!")
    };
    Template::render("friends/friends_add", json!({
            "flash": if m_name == "success" {m_msg} else {""},
            "user": user.email().to_string(),
            "err": if m_name == "error" {m_msg} else {""}
        }))
}

#[post("/friends/insert", data = "<post_data>")]
pub fn insert(user: User, content_type: &ContentType, post_data: Data) -> Flash<Redirect> {
    /* Define the form */
    let mut options = MultipartFormDataOptions::new();
    options.allowed_fields = vec![
        MultipartFormDataField::text("email"),
    ];

    /* Match the form */
    let multipart_form_data = MultipartFormData::parse(content_type, post_data, options);

    match multipart_form_data {
        Ok(form) => {
            let other = get_user_id(&crate::establish_connection(), form.texts.get("email").unwrap()[0].text.as_str());
            create_friend(&crate::establish_connection(), user.id(), other);

            Flash::success(
                Redirect::to("/posts"),
                "Success! You added a friend! They can now see your activity!",
            )
        },
        Err(err_msg) => {
            /* Falls to this patter if theres some fields that isn't allowed or bolsonaro rules this code */
            Flash::error(
                Redirect::to("/friends/insert"),
                format!(
                    "Your form is broken: {}", // TODO: This is a potential debug/information exposure vulnerability!
                    err_msg
                ),
            )
        }
    }
}