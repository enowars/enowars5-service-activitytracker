table! {
    chats (id) {
        id -> Int4,
        user_1 -> Int4,
        user_2 -> Int4,
        name -> Varchar,
    }
}

table! {
    posts (id) {
        id -> Int4,
        body -> Text,
        deleted -> Bool,
    }
}

table! {
    users (id) {
        id -> Int4,
        email -> Varchar,
        password -> Varchar,
        is_admin -> Bool,
    }
}

allow_tables_to_appear_in_same_query!(
    chats,
    posts,
    users,
);
