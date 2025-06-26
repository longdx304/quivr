CREATE TABLE
  IF NOT EXISTS zalo_settings ("key" TEXT PRIMARY KEY, "value" TEXT);

alter table "public"."chats"
add column "zalo_user_id" text null;