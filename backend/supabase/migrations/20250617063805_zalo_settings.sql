create table
  "public"."zalo_settings" (
    "zalo_app_refresh_token" text null,
    "zalo_brain_id" text null
  );

alter table "public"."chats"
add column "zalo_user_id" text null;