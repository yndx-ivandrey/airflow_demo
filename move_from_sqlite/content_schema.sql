DROP SCHEMA IF EXISTS "content" CASCADE;
CREATE SCHEMA "content";

DROP SEQUENCE IF EXISTS "content"."ids";
CREATE SEQUENCE "content"."ids" 
INCREMENT 1
MINVALUE  1
MAXVALUE 9223372036854775807
START 1
CACHE 1;


DROP TABLE IF EXISTS "content"."movies_genre";
CREATE TABLE "content"."movies_genre" (
  "id" uuid PRIMARY KEY,
  "title" varchar(255) NOT NULL
);
CREATE INDEX "movies-genres_id-idx" ON "content"."movies_genre"("id");


DROP TABLE IF EXISTS "content"."movies_movie";
CREATE TABLE "content"."movies_movie" (
  "id" uuid PRIMARY KEY,
  "title" text ,
  "is_suspicious" boolean DEFAULT false ,
  "description" text ,
  "imdb_rating" float4
);
CREATE INDEX "movies-movies_movie-idx" ON "content"."movies_movie"("id");


DROP TABLE IF EXISTS "content"."movies_person";
CREATE TABLE "content"."movies_person" (
  "id" uuid PRIMARY KEY,
  "last_name" char(255) NOT NULL
);
CREATE INDEX "movies_person_id-idx" ON "content"."movies_person"("id");


DROP TABLE IF EXISTS "content"."movies_movie_genres";
CREATE TABLE "content"."movies_movie_genres" (
  "id" int4 NOT NULL DEFAULT nextval('content.ids'::regclass) PRIMARY KEY,
  "movie_id" uuid NOT NULL,
  "genre_id" uuid NOT NULL
);
CREATE UNIQUE INDEX "movies-movies_movie_genres-movie_id-genre_id-idx" ON "content"."movies_movie_genres"("movie_id","genre_id");
CREATE INDEX "movies-movies_movie_genres-genre_id-idx" ON "content"."movies_movie_genres"("genre_id");
ALTER TABLE "content"."movies_genre" ADD CONSTRAINT "unique_title_in_genres" UNIQUE ("title");


DROP TABLE IF EXISTS "content"."movies_movie_actors";
CREATE TABLE "content"."movies_movie_actors" (
  "id" varchar(255)  NOT NULL DEFAULT nextval('content.ids'::regclass) PRIMARY KEY,
  "movie_id" uuid,
  "person_id" uuid
);
CREATE UNIQUE INDEX "movies_movie_actors-movie_id-person_id-idx" ON "content"."movies_movie_actors"("movie_id","person_id");
CREATE INDEX "movies_movie_actors-person_id-idx" ON "content"."movies_movie_actors"("person_id");


DROP TABLE IF EXISTS "content"."movies_movie_directors";
CREATE TABLE "content"."movies_movie_directors" (
  "id" int4 NOT NULL DEFAULT nextval('content.ids'::regclass) PRIMARY KEY,
  "movie_id" uuid,
  "person_id" uuid
);
CREATE UNIQUE INDEX "movies_movie_directors-movie_id-person_id-idx" ON "content"."movies_movie_directors"("movie_id","person_id");
CREATE INDEX "movies_movie_directors-person_id-idx" ON "content"."movies_movie_directors"("person_id");


DROP TABLE IF EXISTS "content"."movies_movie_writers" ;
CREATE TABLE "content"."movies_movie_writers" (
  "id" int4 NOT NULL DEFAULT nextval('content.ids'::regclass) PRIMARY KEY,
  "movie_id" uuid,
  "person_id" uuid
);
CREATE UNIQUE INDEX "movies_movie_writers-movie_id-person_id-idx" ON "content"."movies_movie_writers"("movie_id","person_id");
CREATE INDEX "movies_movie_writersd-person_id-idx" ON "content"."movies_movie_writers"("person_id");


ALTER TABLE "content"."movies_movie_actors" ADD CONSTRAINT "movies_movie_actors_movie_id_fk_movies_movie_id" FOREIGN KEY ("movie_id") REFERENCES "content"."movies_movie" ("id") ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE "content"."movies_movie_actors" ADD CONSTRAINT "movies_movie_actors_person_id_fk_movies_person_id" FOREIGN KEY ("person_id") REFERENCES "content"."movies_person" ("id") ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE "content"."movies_movie_directors" ADD CONSTRAINT "movies_movie_directors_movie_id_fk_movies_movie_id" FOREIGN KEY ("movie_id") REFERENCES "content"."movies_movie" ("id") ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE "content"."movies_movie_directors" ADD CONSTRAINT "movies_movie_directors_person_id_fk_movies_person_id" FOREIGN KEY ("person_id") REFERENCES "content"."movies_person" ("id") ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE "content"."movies_movie_genres" ADD CONSTRAINT "movies_movie_genres_genre_id_fk_movies_genre_id" FOREIGN KEY ("genre_id") REFERENCES "content"."movies_genre" ("id") ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE "content"."movies_movie_genres" ADD CONSTRAINT "movies_movie_genres_movie_id_fk_movies_movie_id" FOREIGN KEY ("movie_id") REFERENCES "content"."movies_movie" ("id") ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE "content"."movies_movie_writers" ADD CONSTRAINT "movies_movie_writers_movie_id_fk_movies_movie_id" FOREIGN KEY ("movie_id") REFERENCES "content"."movies_movie" ("id") ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE "content"."movies_movie_writers" ADD CONSTRAINT "movies_movie_writers_person_id_fk_movies_person_id" FOREIGN KEY ("person_id") REFERENCES "content"."movies_person" ("id") ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED;
