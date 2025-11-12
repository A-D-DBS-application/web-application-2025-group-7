[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/DxqGQVx4)



-- Tabellen voor PostgreSQL


1) CREATE TABLE public.beschikbaarheid (
  beschikbaarheid_id integer NOT NULL DEFAULT nextval('beschikbaarheid_beschikbaarheid_id_seq'::regclass),
  kot_id integer,
  startdatum timestamp without time zone NOT NULL,
  einddatum timestamp without time zone NOT NULL,
  status_beschikbaarheid character varying CHECK (status_beschikbaarheid::text = ANY (ARRAY['beschikbaar'::character varying, 'bezet'::character varying, 'onder_optie'::character varying]::text[])),
  CONSTRAINT beschikbaarheid_pkey PRIMARY KEY (beschikbaarheid_id),
  CONSTRAINT beschikbaarheid_kot_id_fkey FOREIGN KEY (kot_id) REFERENCES public.kot(kot_id)
);
2) CREATE TABLE public.boeking (
  boeking_id integer NOT NULL DEFAULT nextval('boeking_boeking_id_seq'::regclass),
  gebruiker_id integer,
  kot_id integer,
  startdatum timestamp without time zone NOT NULL,
  einddatum timestamp without time zone NOT NULL,
  totaalprijs numeric,
  status_boeking character varying CHECK (status_boeking::text = ANY (ARRAY['in afwachting'::character varying::text, 'bevestigd'::character varying::text, 'geannuleerd'::character varying::text])),
  CONSTRAINT boeking_pkey PRIMARY KEY (boeking_id),
  CONSTRAINT boeking_kot_id_fkey FOREIGN KEY (kot_id) REFERENCES public.kot(kot_id),
  CONSTRAINT boeking_gebruiker_id_fkey FOREIGN KEY (gebruiker_id) REFERENCES public.huurder(gebruiker_id)
);
3) CREATE TABLE public.gebruiker (
  gebruiker_id integer NOT NULL DEFAULT nextval('gebruiker_gebruiker_id_seq'::regclass),
  naam character varying NOT NULL,
  email character varying NOT NULL UNIQUE,
  telefoon character varying,
  type character varying CHECK (type::text = ANY (ARRAY['student'::character varying, 'huurder'::character varying, 'kotbaas'::character varying]::text[])),
  aangemaakt_op timestamp without time zone DEFAULT now(),
  CONSTRAINT gebruiker_pkey PRIMARY KEY (gebruiker_id)
);
4) REATE TABLE public.huurder (
  gebruiker_id integer NOT NULL,
  voorkeuren text DEFAULT ''::text,
  gesproken_taal character varying,
  CONSTRAINT huurder_pkey PRIMARY KEY (gebruiker_id),
  CONSTRAINT huurder_gebruiker_id_fkey FOREIGN KEY (gebruiker_id) REFERENCES public.gebruiker(gebruiker_id)
);
5) CREATE TABLE public.kot (
  kot_id integer NOT NULL DEFAULT nextval('kot_kot_id_seq'::regclass),
  student_id integer,
  adres character varying NOT NULL,
  stad character varying NOT NULL,
  oppervlakte integer,
  aantal_slaapplaatsen integer,
  maandhuurprijs real NOT NULL,
  brandveiligheidsconformiteit boolean DEFAULT true,
  eigen_keuken boolean DEFAULT false,
  eigen_sanitair boolean DEFAULT false,
  egwkosten real,
  goedgekeurd boolean DEFAULT false,
  foto text,
  CONSTRAINT kot_pkey PRIMARY KEY (kot_id),
  CONSTRAINT kot_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.student(gebruiker_id)
);
6) CREATE TABLE public.student (
  gebruiker_id integer NOT NULL,
  universiteit character varying,
  initiatiefnemer boolean DEFAULT false,
  CONSTRAINT student_pkey PRIMARY KEY (gebruiker_id),
  CONSTRAINT student_gebruiker_id_fkey FOREIGN KEY (gebruiker_id) REFERENCES public.gebruiker(gebruiker_id)
);