[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/DxqGQVx4)

-- Tabellen voor PostgreSQL

1) CREATE TABLE public.beschikbaarheid (
  beschikbaarheid_id integer NOT NULL,
  kot_id integer,
  startdatum date,
  einddatum date,
  status text,
  createdat timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT beschikbaarheid_pkey PRIMARY KEY (beschikbaarheid_id),
  CONSTRAINT beschikbaarheid_kot_id_fkey FOREIGN KEY (kot_id) REFERENCES public.kot(kot_id)
);
2) CREATE TABLE public.boeking (
  boeking_id integer NOT NULL,
  huurder_id integer,
  kot_id integer,
  startdatum date,
  einddatum date,
  totaalprijs numeric,
  status text,
  createdat timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT boeking_pkey PRIMARY KEY (boeking_id),
  CONSTRAINT boeking_huurder_id_fkey FOREIGN KEY (huurder_id) REFERENCES public.huurder(huurder_id),
  CONSTRAINT boeking_kot_id_fkey FOREIGN KEY (kot_id) REFERENCES public.kot(kot_id)
);
3) CREATE TABLE public.huurder (
  huurder_id integer NOT NULL,
  naam text,
  email text,
  telefoon text,
  voorkeuren text,
  land text,
  createdat timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT huurder_pkey PRIMARY KEY (huurder_id)
);
4) CREATE TABLE public.kot (
  kot_id integer NOT NULL,
  adres text,
  stad text,
  oppervlakte integer,
  aantal_slaapplaatsen integer,
  prijs_per_nacht numeric,
  eigen_keuken boolean,
  eigen_sanitair boolean,
  egw_kosten numeric,
  goedgekeurd boolean,
  student_id integer,
  kotbaas_id integer,
  created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT kot_pkey PRIMARY KEY (kot_id),
  CONSTRAINT kot_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.student(student_id)
);
5) CREATE TABLE public.student (
  student_id integer NOT NULL DEFAULT nextval('student_student_id_seq'::regclass),
  naam text NOT NULL,
  email text NOT NULL UNIQUE,
  telefoon text,
  universiteit text,
  createdat timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT student_pkey PRIMARY KEY (student_id)
);