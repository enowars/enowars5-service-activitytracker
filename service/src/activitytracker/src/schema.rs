table! {
    chats (id) {
        id -> Int4,
        user_1 -> Int4,
        user_2 -> Int4,
        name -> Varchar,
    }
}

table! {
    friends (id) {
        id -> Int4,
        sender_id -> Int4,
        receiver_id -> Int4,
    }
}

table! {
    posts (id) {
        id -> Int4,
        body -> Text,
        deleted -> Bool,
        visibility -> Text,
        image -> Nullable<Text>,
        user_id -> Int4,
        user_post_count -> Int4,
        protected -> Bool,
    }
}

table! {
    users (id) {
        id -> Int4,
        email -> Varchar,
        password -> Varchar,
        is_admin -> Bool,
        verification_image -> Text,
        post_count -> Int4,
    }
}

joinable!(posts -> users (user_id));

allow_tables_to_appear_in_same_query!(
    chats,
    friends,
    posts,
    users,
);
