--
-- PostgreSQL database dump
--

\restrict PipeJpBbM3IWXSfRVViFmmm7TSupJDCps9W1d98wUIYwOcVPErP66SVQNdPwyhR

-- Dumped from database version 16.13
-- Dumped by pg_dump version 16.13

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: academicperiods; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.academicperiods (
    id integer NOT NULL,
    year_id integer,
    cycle_id integer,
    period_name_ar text,
    period_name_fr text,
    sort_order integer
);


ALTER TABLE public.academicperiods OWNER TO postgres;

--
-- Name: academicperiods_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.academicperiods_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.academicperiods_id_seq OWNER TO postgres;

--
-- Name: academicperiods_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.academicperiods_id_seq OWNED BY public.academicperiods.id;


--
-- Name: academicyears; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.academicyears (
    id integer NOT NULL,
    year_label text NOT NULL,
    is_active integer DEFAULT 0,
    school_id integer DEFAULT 1
);


ALTER TABLE public.academicyears OWNER TO postgres;

--
-- Name: academicyears_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.academicyears_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.academicyears_id_seq OWNER TO postgres;

--
-- Name: academicyears_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.academicyears_id_seq OWNED BY public.academicyears.id;


--
-- Name: assessmenttypes; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.assessmenttypes (
    id integer NOT NULL,
    period_id integer,
    name_ar text,
    name_fr text,
    type_code text,
    weight_percentage real DEFAULT 1.0
);


ALTER TABLE public.assessmenttypes OWNER TO postgres;

--
-- Name: assessmenttypes_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.assessmenttypes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.assessmenttypes_id_seq OWNER TO postgres;

--
-- Name: assessmenttypes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.assessmenttypes_id_seq OWNED BY public.assessmenttypes.id;


--
-- Name: auditlogs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.auditlogs (
    id integer NOT NULL,
    actor text,
    action text,
    target text,
    "timestamp" timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.auditlogs OWNER TO postgres;

--
-- Name: auditlogs_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.auditlogs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.auditlogs_id_seq OWNER TO postgres;

--
-- Name: auditlogs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.auditlogs_id_seq OWNED BY public.auditlogs.id;


--
-- Name: classes; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.classes (
    id integer NOT NULL,
    cycle_id integer,
    class_name_ar text,
    class_name_fr text,
    sort_order integer DEFAULT 0,
    school_id integer DEFAULT 1
);


ALTER TABLE public.classes OWNER TO postgres;

--
-- Name: classes_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.classes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.classes_id_seq OWNER TO postgres;

--
-- Name: classes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.classes_id_seq OWNED BY public.classes.id;


--
-- Name: cycles; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.cycles (
    id integer NOT NULL,
    name_ar text,
    name_fr text
);


ALTER TABLE public.cycles OWNER TO postgres;

--
-- Name: cycles_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.cycles_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.cycles_id_seq OWNER TO postgres;

--
-- Name: cycles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.cycles_id_seq OWNED BY public.cycles.id;


--
-- Name: emailsettings; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.emailsettings (
    id integer NOT NULL,
    smtp_server text,
    smtp_port text,
    email_address text,
    email_password text
);


ALTER TABLE public.emailsettings OWNER TO postgres;

--
-- Name: emailsettings_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.emailsettings_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.emailsettings_id_seq OWNER TO postgres;

--
-- Name: emailsettings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.emailsettings_id_seq OWNED BY public.emailsettings.id;


--
-- Name: expenses; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.expenses (
    id integer NOT NULL,
    category text,
    amount real,
    description text,
    expense_date date,
    paid_to text,
    created_at text
);


ALTER TABLE public.expenses OWNER TO postgres;

--
-- Name: expenses_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.expenses_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.expenses_id_seq OWNER TO postgres;

--
-- Name: expenses_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.expenses_id_seq OWNED BY public.expenses.id;


--
-- Name: grades; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.grades (
    id integer NOT NULL,
    student_id integer,
    subject_id integer,
    assessment_id integer,
    score real,
    observation text,
    date_recorded text,
    year_id integer
);


ALTER TABLE public.grades OWNER TO postgres;

--
-- Name: grades_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.grades_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.grades_id_seq OWNER TO postgres;

--
-- Name: grades_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.grades_id_seq OWNED BY public.grades.id;


--
-- Name: inventoryitems; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.inventoryitems (
    id integer NOT NULL,
    name_fr text,
    name_ar text,
    category text,
    quantity integer DEFAULT 0,
    min_quantity integer DEFAULT 5,
    unit_price real DEFAULT 0.0,
    location text
);


ALTER TABLE public.inventoryitems OWNER TO postgres;

--
-- Name: inventoryitems_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.inventoryitems_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.inventoryitems_id_seq OWNER TO postgres;

--
-- Name: inventoryitems_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.inventoryitems_id_seq OWNED BY public.inventoryitems.id;


--
-- Name: inventorylog; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.inventorylog (
    id integer NOT NULL,
    item_id integer,
    transaction_type text,
    quantity integer,
    transaction_date text,
    notes text,
    performed_by text,
    expense_id integer
);


ALTER TABLE public.inventorylog OWNER TO postgres;

--
-- Name: inventorylog_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.inventorylog_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.inventorylog_id_seq OWNER TO postgres;

--
-- Name: inventorylog_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.inventorylog_id_seq OWNED BY public.inventorylog.id;


--
-- Name: monthlyfeeschedule; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.monthlyfeeschedule (
    id integer NOT NULL,
    class_id integer,
    month_index integer,
    month_name text,
    amount real
);


ALTER TABLE public.monthlyfeeschedule OWNER TO postgres;

--
-- Name: monthlyfeeschedule_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.monthlyfeeschedule_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.monthlyfeeschedule_id_seq OWNER TO postgres;

--
-- Name: monthlyfeeschedule_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.monthlyfeeschedule_id_seq OWNED BY public.monthlyfeeschedule.id;


--
-- Name: monthlypaymentsstatus; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.monthlypaymentsstatus (
    id integer NOT NULL,
    student_id integer,
    month_index integer,
    due_id integer,
    payment_id integer,
    amount_paid real
);


ALTER TABLE public.monthlypaymentsstatus OWNER TO postgres;

--
-- Name: monthlypaymentsstatus_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.monthlypaymentsstatus_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.monthlypaymentsstatus_id_seq OWNER TO postgres;

--
-- Name: monthlypaymentsstatus_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.monthlypaymentsstatus_id_seq OWNED BY public.monthlypaymentsstatus.id;


--
-- Name: notificationlogs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.notificationlogs (
    id integer NOT NULL,
    recipient_type text,
    recipient_contact text,
    subject text,
    status text,
    error_msg text,
    sent_at text
);


ALTER TABLE public.notificationlogs OWNER TO postgres;

--
-- Name: notificationlogs_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.notificationlogs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.notificationlogs_id_seq OWNER TO postgres;

--
-- Name: notificationlogs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.notificationlogs_id_seq OWNED BY public.notificationlogs.id;


--
-- Name: payments; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.payments (
    id integer NOT NULL,
    student_id integer,
    year_id integer,
    transaction_date timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    total_due real,
    discount real DEFAULT 0,
    amount_paid real,
    remaining_balance real,
    payment_type text,
    details text
);


ALTER TABLE public.payments OWNER TO postgres;

--
-- Name: payments_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.payments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.payments_id_seq OWNER TO postgres;

--
-- Name: payments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.payments_id_seq OWNED BY public.payments.id;


--
-- Name: registrationfees; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.registrationfees (
    id integer NOT NULL,
    class_id integer,
    amount real
);


ALTER TABLE public.registrationfees OWNER TO postgres;

--
-- Name: registrationfees_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.registrationfees_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.registrationfees_id_seq OWNER TO postgres;

--
-- Name: registrationfees_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.registrationfees_id_seq OWNED BY public.registrationfees.id;


--
-- Name: salaryslips; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.salaryslips (
    id integer NOT NULL,
    staff_id integer,
    month_str text,
    basic_amount real,
    hours_worked real,
    bonuses real,
    deductions real,
    net_amount real,
    payment_date text
);


ALTER TABLE public.salaryslips OWNER TO postgres;

--
-- Name: salaryslips_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.salaryslips_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.salaryslips_id_seq OWNER TO postgres;

--
-- Name: salaryslips_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.salaryslips_id_seq OWNED BY public.salaryslips.id;


--
-- Name: schoolinfo; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.schoolinfo (
    id integer NOT NULL,
    republic text,
    ia text,
    ief text,
    school_name text,
    auth_number text,
    address text,
    phone text,
    logo_path text,
    director_name text
);


ALTER TABLE public.schoolinfo OWNER TO postgres;

--
-- Name: schoolinfo_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.schoolinfo_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.schoolinfo_id_seq OWNER TO postgres;

--
-- Name: schoolinfo_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.schoolinfo_id_seq OWNED BY public.schoolinfo.id;


--
-- Name: schools; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.schools (
    id integer NOT NULL,
    name text NOT NULL,
    code text,
    is_active integer DEFAULT 1,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.schools OWNER TO postgres;

--
-- Name: schools_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.schools_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.schools_id_seq OWNER TO postgres;

--
-- Name: schools_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.schools_id_seq OWNED BY public.schools.id;


--
-- Name: staff; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.staff (
    id integer NOT NULL,
    first_name text,
    last_name text,
    role text,
    specialty text,
    phone text,
    email text,
    address text,
    hire_date text,
    contract_type text DEFAULT 'Monthly'::text,
    salary_base real DEFAULT 0,
    hourly_rate real DEFAULT 0,
    photo_path text,
    status text DEFAULT 'Actif'::text,
    school_id integer DEFAULT 1
);


ALTER TABLE public.staff OWNER TO postgres;

--
-- Name: staff_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.staff_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.staff_id_seq OWNER TO postgres;

--
-- Name: staff_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.staff_id_seq OWNED BY public.staff.id;


--
-- Name: staffattendance; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.staffattendance (
    id integer NOT NULL,
    staff_id integer,
    attendance_date text,
    check_in_time text,
    check_out_time text,
    status text,
    note text
);


ALTER TABLE public.staffattendance OWNER TO postgres;

--
-- Name: staffattendance_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.staffattendance_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.staffattendance_id_seq OWNER TO postgres;

--
-- Name: staffattendance_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.staffattendance_id_seq OWNED BY public.staffattendance.id;


--
-- Name: staffleaves; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.staffleaves (
    id integer NOT NULL,
    staff_id integer,
    leave_type text,
    start_date date,
    end_date date,
    days_count integer,
    reason text,
    status text DEFAULT 'En Attente'::text
);


ALTER TABLE public.staffleaves OWNER TO postgres;

--
-- Name: staffleaves_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.staffleaves_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.staffleaves_id_seq OWNER TO postgres;

--
-- Name: staffleaves_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.staffleaves_id_seq OWNED BY public.staffleaves.id;


--
-- Name: studentattendance; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.studentattendance (
    id integer NOT NULL,
    student_id integer,
    date date,
    status text,
    justifie integer DEFAULT 0,
    reason text,
    notes text,
    year_id integer,
    period_id integer,
    recorded_by text
);


ALTER TABLE public.studentattendance OWNER TO postgres;

--
-- Name: studentattendance_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.studentattendance_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.studentattendance_id_seq OWNER TO postgres;

--
-- Name: studentattendance_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.studentattendance_id_seq OWNED BY public.studentattendance.id;


--
-- Name: studentclassnumbers; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.studentclassnumbers (
    id integer NOT NULL,
    student_id integer,
    class_id integer,
    year_id integer,
    class_number integer,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.studentclassnumbers OWNER TO postgres;

--
-- Name: studentclassnumbers_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.studentclassnumbers_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.studentclassnumbers_id_seq OWNER TO postgres;

--
-- Name: studentclassnumbers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.studentclassnumbers_id_seq OWNED BY public.studentclassnumbers.id;


--
-- Name: studentdiscipline; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.studentdiscipline (
    id integer NOT NULL,
    student_id integer,
    incident_date date,
    incident_type text,
    sanction text,
    points_deducted real DEFAULT 0,
    observation text,
    year_id integer,
    period_id integer
);


ALTER TABLE public.studentdiscipline OWNER TO postgres;

--
-- Name: studentdiscipline_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.studentdiscipline_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.studentdiscipline_id_seq OWNER TO postgres;

--
-- Name: studentdiscipline_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.studentdiscipline_id_seq OWNED BY public.studentdiscipline.id;


--
-- Name: studentdues; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.studentdues (
    id integer NOT NULL,
    student_id integer,
    year_id integer,
    fee_type text,
    fee_description text,
    original_amount real,
    discount_amount real DEFAULT 0,
    net_amount real,
    due_date date,
    is_paid integer DEFAULT 0
);


ALTER TABLE public.studentdues OWNER TO postgres;

--
-- Name: studentdues_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.studentdues_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.studentdues_id_seq OWNER TO postgres;

--
-- Name: studentdues_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.studentdues_id_seq OWNED BY public.studentdues.id;


--
-- Name: students; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.students (
    id integer NOT NULL,
    first_name_fr text NOT NULL,
    last_name_fr text NOT NULL,
    first_name_ar text NOT NULL,
    last_name_ar text NOT NULL,
    birth_date date,
    birth_place text,
    gender text,
    address text,
    parent_name text,
    parent_phone text,
    parent_email text,
    parent_address text,
    registration_date date DEFAULT CURRENT_DATE,
    status text DEFAULT 'Active'::text,
    photo_path text,
    parent_pin text,
    school_id integer DEFAULT 1,
    student_code text,
    parent_pin_hash text
);


ALTER TABLE public.students OWNER TO postgres;

--
-- Name: students_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.students_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.students_id_seq OWNER TO postgres;

--
-- Name: students_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.students_id_seq OWNED BY public.students.id;


--
-- Name: subjects; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.subjects (
    id integer NOT NULL,
    cycle_id integer,
    subject_name_ar text,
    subject_name_fr text,
    coefficient real DEFAULT 1,
    subject_lang text DEFAULT 'Français'::text
);


ALTER TABLE public.subjects OWNER TO postgres;

--
-- Name: subjects_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.subjects_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.subjects_id_seq OWNER TO postgres;

--
-- Name: subjects_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.subjects_id_seq OWNED BY public.subjects.id;


--
-- Name: timetable; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.timetable (
    id integer NOT NULL,
    class_id integer,
    day_of_week text,
    start_time text,
    end_time text,
    subject_id integer,
    teacher_id integer,
    room text
);


ALTER TABLE public.timetable OWNER TO postgres;

--
-- Name: timetable_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.timetable_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.timetable_id_seq OWNER TO postgres;

--
-- Name: timetable_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.timetable_id_seq OWNED BY public.timetable.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    id integer NOT NULL,
    staff_id integer,
    username text NOT NULL,
    email text,
    password_hash text NOT NULL,
    role text DEFAULT 'User'::text,
    status text DEFAULT 'Actif'::text,
    created_date timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.users OWNER TO postgres;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_id_seq OWNER TO postgres;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: academicperiods id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.academicperiods ALTER COLUMN id SET DEFAULT nextval('public.academicperiods_id_seq'::regclass);


--
-- Name: academicyears id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.academicyears ALTER COLUMN id SET DEFAULT nextval('public.academicyears_id_seq'::regclass);


--
-- Name: assessmenttypes id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.assessmenttypes ALTER COLUMN id SET DEFAULT nextval('public.assessmenttypes_id_seq'::regclass);


--
-- Name: auditlogs id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auditlogs ALTER COLUMN id SET DEFAULT nextval('public.auditlogs_id_seq'::regclass);


--
-- Name: classes id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.classes ALTER COLUMN id SET DEFAULT nextval('public.classes_id_seq'::regclass);


--
-- Name: cycles id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.cycles ALTER COLUMN id SET DEFAULT nextval('public.cycles_id_seq'::regclass);


--
-- Name: emailsettings id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.emailsettings ALTER COLUMN id SET DEFAULT nextval('public.emailsettings_id_seq'::regclass);


--
-- Name: expenses id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.expenses ALTER COLUMN id SET DEFAULT nextval('public.expenses_id_seq'::regclass);


--
-- Name: grades id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.grades ALTER COLUMN id SET DEFAULT nextval('public.grades_id_seq'::regclass);


--
-- Name: inventoryitems id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.inventoryitems ALTER COLUMN id SET DEFAULT nextval('public.inventoryitems_id_seq'::regclass);


--
-- Name: inventorylog id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.inventorylog ALTER COLUMN id SET DEFAULT nextval('public.inventorylog_id_seq'::regclass);


--
-- Name: monthlyfeeschedule id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.monthlyfeeschedule ALTER COLUMN id SET DEFAULT nextval('public.monthlyfeeschedule_id_seq'::regclass);


--
-- Name: monthlypaymentsstatus id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.monthlypaymentsstatus ALTER COLUMN id SET DEFAULT nextval('public.monthlypaymentsstatus_id_seq'::regclass);


--
-- Name: notificationlogs id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.notificationlogs ALTER COLUMN id SET DEFAULT nextval('public.notificationlogs_id_seq'::regclass);


--
-- Name: payments id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.payments ALTER COLUMN id SET DEFAULT nextval('public.payments_id_seq'::regclass);


--
-- Name: registrationfees id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.registrationfees ALTER COLUMN id SET DEFAULT nextval('public.registrationfees_id_seq'::regclass);


--
-- Name: salaryslips id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.salaryslips ALTER COLUMN id SET DEFAULT nextval('public.salaryslips_id_seq'::regclass);


--
-- Name: schoolinfo id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.schoolinfo ALTER COLUMN id SET DEFAULT nextval('public.schoolinfo_id_seq'::regclass);


--
-- Name: schools id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.schools ALTER COLUMN id SET DEFAULT nextval('public.schools_id_seq'::regclass);


--
-- Name: staff id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.staff ALTER COLUMN id SET DEFAULT nextval('public.staff_id_seq'::regclass);


--
-- Name: staffattendance id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.staffattendance ALTER COLUMN id SET DEFAULT nextval('public.staffattendance_id_seq'::regclass);


--
-- Name: staffleaves id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.staffleaves ALTER COLUMN id SET DEFAULT nextval('public.staffleaves_id_seq'::regclass);


--
-- Name: studentattendance id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.studentattendance ALTER COLUMN id SET DEFAULT nextval('public.studentattendance_id_seq'::regclass);


--
-- Name: studentclassnumbers id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.studentclassnumbers ALTER COLUMN id SET DEFAULT nextval('public.studentclassnumbers_id_seq'::regclass);


--
-- Name: studentdiscipline id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.studentdiscipline ALTER COLUMN id SET DEFAULT nextval('public.studentdiscipline_id_seq'::regclass);


--
-- Name: studentdues id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.studentdues ALTER COLUMN id SET DEFAULT nextval('public.studentdues_id_seq'::regclass);


--
-- Name: students id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.students ALTER COLUMN id SET DEFAULT nextval('public.students_id_seq'::regclass);


--
-- Name: subjects id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.subjects ALTER COLUMN id SET DEFAULT nextval('public.subjects_id_seq'::regclass);


--
-- Name: timetable id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.timetable ALTER COLUMN id SET DEFAULT nextval('public.timetable_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Data for Name: academicperiods; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.academicperiods (id, year_id, cycle_id, period_name_ar, period_name_fr, sort_order) FROM stdin;
1	1	1	الفصل الأول	Trimestre 1	1
2	1	1	الفصل الثاني	Trimestre 2	2
3	1	1	الفصل الثالث	Trimestre 3	3
4	2	1	الفصل الأول	Trimestre 1	1
5	2	1	الفصل الثاني	Trimestre 2	2
6	2	1	الفصل الثالث	Trimestre 3	3
\.


--
-- Data for Name: academicyears; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.academicyears (id, year_label, is_active, school_id) FROM stdin;
2	2026-2027	0	1
1	2025-2026	1	1
\.


--
-- Data for Name: assessmenttypes; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.assessmenttypes (id, period_id, name_ar, name_fr, type_code, weight_percentage) FROM stdin;
1	1	اختبار فصلي	Composition	COMPO	1
2	2	اختبار فصلي	Composition	COMPO	1
3	3	اختبار فصلي	Composition	COMPO	1
4	4	اختبار فصلي	Composition	COMPO	1
5	5	اختبار فصلي	Composition	COMPO	1
6	6	اختبار فصلي	Composition	COMPO	1
\.


--
-- Data for Name: auditlogs; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.auditlogs (id, actor, action, target, "timestamp") FROM stdin;
1	System	Auto-Create	admin	2026-04-04 00:26:50
2	Admin	Add User	Com	2026-04-26 10:42:53
3	Admin	Reset Password	Com	2026-05-01 11:11:27
4	wizard	ADMIN_SETUP	admin	2026-05-01 23:44:22.102198
5	admin	LOGIN	admin	2026-05-01 23:44:40.826946
6	admin	LOGIN_FAILED	admin	2026-05-02 06:35:06.797931
7	admin	LOGIN	admin	2026-05-02 06:35:23.115397
8	admin	LOGIN	admin	2026-05-07 18:11:05.689644
9	admin	LOGIN	admin	2026-05-07 18:12:23.69274
10	admin	LOGIN	admin	2026-05-08 20:12:31.577534
11	admin	LOGIN	admin	2026-05-08 21:22:03.490371
12	admin	LOGIN	admin	2026-05-08 23:06:34.883424
13	admin	LOGIN	admin	2026-05-08 23:16:33.251895
14	admin	LOGIN	admin	2026-05-08 23:17:31.699948
15	admin	LOGIN	admin	2026-05-15 21:21:06.446839
16	admin	LOGIN_FAILED	admin	2026-05-16 21:24:59.993085
17	admin	LOGIN	admin	2026-05-16 21:25:20.911331
18	Admin	DELETE_USER	Com	2026-05-16 21:27:45.162598
\.


--
-- Data for Name: classes; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.classes (id, cycle_id, class_name_ar, class_name_fr, sort_order, school_id) FROM stdin;
1	1		Jardin	1	1
2	1	التحضير الأول	CI	2	1
\.


--
-- Data for Name: cycles; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.cycles (id, name_ar, name_fr) FROM stdin;
1		elemantaire
\.


--
-- Data for Name: emailsettings; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.emailsettings (id, smtp_server, smtp_port, email_address, email_password) FROM stdin;
3	smtp.gmail.com	587	thioyeawa877@gmail.com	soblzvahcgbmfiyx
\.


--
-- Data for Name: expenses; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.expenses (id, category, amount, description, expense_date, paid_to, created_at) FROM stdin;
1	Loyer	2000	Cree	2026-04-07	JARDIN	\N
2	Salaire	4500	Salaire 2026-04 - Staff ID 1	2026-04-07	Personnel	\N
\.


--
-- Data for Name: grades; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.grades (id, student_id, subject_id, assessment_id, score, observation, date_recorded, year_id) FROM stdin;
1	2	1	1	8		2026-04-07	1
2	1	1	1	7		2026-04-07	1
3	2	1	2	7		2026-04-26	1
4	1	1	2	8		2026-04-26	1
5	3	1	2	9		2026-04-26	1
\.


--
-- Data for Name: inventoryitems; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.inventoryitems (id, name_fr, name_ar, category, quantity, min_quantity, unit_price, location) FROM stdin;
1	eponse	اسفنج	Hygiène (نظافة)	4	5	100	tiroire 1
\.


--
-- Data for Name: inventorylog; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.inventorylog (id, item_id, transaction_type, quantity, transaction_date, notes, performed_by, expense_id) FROM stdin;
1	1	IN	5	2026-04-26 11:24:02	Stock Initial	\N	\N
2	1	OUT	1	2026-04-26 11:24:44	CI	\N	\N
\.


--
-- Data for Name: monthlyfeeschedule; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.monthlyfeeschedule (id, class_id, month_index, month_name, amount) FROM stdin;
10	1	10	Octobre / أكتوبر	5000
11	1	11	Novembre / نوفمبر	5000
12	1	12	Décembre / ديسمبر	5000
13	1	1	Janvier / يناير	5000
14	1	2	Février / فبراير	6250
15	1	3	Mars / مارس	6250
16	1	4	Avril / أبريل	6250
17	1	5	Mai / مايو	6250
18	1	6	Juin / يونيو	0
\.


--
-- Data for Name: monthlypaymentsstatus; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.monthlypaymentsstatus (id, student_id, month_index, due_id, payment_id, amount_paid) FROM stdin;
1	1	1	1	1	1500
\.


--
-- Data for Name: notificationlogs; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.notificationlogs (id, recipient_type, recipient_contact, subject, status, error_msg, sent_at) FROM stdin;
1	\N	Connection	Réuuinion	Erreur SMTP	[Errno 11001] getaddrinfo failed	2026-04-26 12:18:32
2	\N	Connection	Réuuinion	Erreur SMTP	[Errno 11001] getaddrinfo failed	2026-04-26 12:19:03
3	\N	Connection	Réuuinion	Erreur SMTP	[Errno 11001] getaddrinfo failed	2026-04-26 12:21:28
4	\N	malikdiouf868@gmail.com	Réuuinion	Envoyé		2026-04-26 12:22:23
5	\N	malikdiouf868@gmail.com	Réuuinion	Envoyé		2026-04-26 12:22:52
6	\N	loukh@gimail.com	Réuuinion	Envoyé		2026-04-26 12:23:20
\.


--
-- Data for Name: payments; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.payments (id, student_id, year_id, transaction_date, total_due, discount, amount_paid, remaining_balance, payment_type, details) FROM stdin;
1	1	1	2026-04-07 23:05:12	1500	0	1500	0	Invoice Payment	Frais d'inscription
\.


--
-- Data for Name: registrationfees; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.registrationfees (id, class_id, amount) FROM stdin;
1	1	1500
\.


--
-- Data for Name: salaryslips; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.salaryslips (id, staff_id, month_str, basic_amount, hours_worked, bonuses, deductions, net_amount, payment_date) FROM stdin;
1	1	2026-04	4500	9	0	0	4500	2026-04-07 23:08:39
\.


--
-- Data for Name: schoolinfo; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.schoolinfo (id, republic, ia, ief, school_name, auth_number, address, phone, logo_path, director_name) FROM stdin;
3	Senegal	Pikine	Keur Massar	El Malick School Management System	25	Boune	77 099 99 00	C:/Users/EL MALICK/OneDrive/Documents/DOSSIER DHH 2025-2026/LOGO DHH BLEU .jpg	
\.


--
-- Data for Name: schools; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.schools (id, name, code, is_active, created_at) FROM stdin;
1	École Principale	MAIN	1	2026-05-01 21:52:53.18963
\.


--
-- Data for Name: staff; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.staff (id, first_name, last_name, role, specialty, phone, email, address, hire_date, contract_type, salary_base, hourly_rate, photo_path, status, school_id) FROM stdin;
1	Bouba	Diouf	Professeur			elmalickdiouf26@gmail.com		2026-04-06	Hourly	0	500	staff_photos\\staff_20260407220349.jpg	Actif	1
\.


--
-- Data for Name: staffattendance; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.staffattendance (id, staff_id, attendance_date, check_in_time, check_out_time, status, note) FROM stdin;
1	1	2026-04-07	08:00	17:00	Présent	
2	1	2026-04-26	08:00	16:00	Présent	
\.


--
-- Data for Name: staffleaves; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.staffleaves (id, staff_id, leave_type, start_date, end_date, days_count, reason, status) FROM stdin;
2	1	Maladie	2026-04-26	2026-04-26	1	code	Approuvé
1	1	Maladie	2026-04-07	2026-04-07	1	KJLN FDS JK KLNdsNKLN KN LDs  	Rejeté
\.


--
-- Data for Name: studentattendance; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.studentattendance (id, student_id, date, status, justifie, reason, notes, year_id, period_id, recorded_by) FROM stdin;
1	2	2026-04-07	Présent	0			1	1	\N
2	1	2026-04-07	Présent	0			1	1	\N
3	2	2026-04-26	Absent	1			1	2	\N
4	3	2026-04-26	Absent	0			1	2	\N
5	1	2026-04-26	Présent	0			1	2	\N
\.


--
-- Data for Name: studentclassnumbers; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.studentclassnumbers (id, student_id, class_id, year_id, class_number, created_at) FROM stdin;
1	1	1	1	1	2026-04-04 23:10:01.106053
2	2	1	1	2	2026-04-06 22:04:04.177553
3	3	1	1	3	2026-04-26 10:51:46.006498
4	1	2	2	1	2026-04-26 12:45:13.574193
5	2	2	2	2	2026-04-26 12:45:13.574193
6	3	1	2	1	2026-04-26 12:45:13.574193
\.


--
-- Data for Name: studentdiscipline; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.studentdiscipline (id, student_id, incident_date, incident_type, sanction, points_deducted, observation, year_id, period_id) FROM stdin;
1	1	2026-04-07	Non port de la tenue / عدم ارتداء الزي	Frapper	1	hbbjkj oàiçôiji hçjk hjoi 	1	1
2	1	2026-04-26	Insolence / وقاحة	boulé	2		1	2
\.


--
-- Data for Name: studentdues; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.studentdues (id, student_id, year_id, fee_type, fee_description, original_amount, discount_amount, net_amount, due_date, is_paid) FROM stdin;
2	1	1	Month_10	Mensualité Octobre / أكتوبر	5000	0	5000	2026-10-05	0
3	1	1	Month_11	Mensualité Novembre / نوفمبر	5000	0	5000	2026-11-05	0
4	1	1	Month_12	Mensualité Décembre / ديسمبر	5000	0	5000	2026-12-05	0
5	1	1	Month_1	Mensualité Janvier / يناير	5000	0	5000	2027-01-05	0
6	1	1	Month_2	Mensualité Février / فبراير	6250	0	6250	2027-02-05	0
7	1	1	Month_3	Mensualité Mars / مارس	6250	0	6250	2027-03-05	0
8	1	1	Month_4	Mensualité Avril / أبريل	6250	0	6250	2027-04-05	0
9	1	1	Month_5	Mensualité Mai / مايو	6250	0	6250	2027-05-05	0
10	1	1	Month_6	Mensualité Juin / يونيو	0	0	0	2027-06-05	0
11	2	1	Registration	Frais d'inscription	1500	0	1500	2026-04-07	0
12	2	1	Month_10	Mensualité Octobre / أكتوبر	5000	0	5000	2026-10-05	0
13	2	1	Month_11	Mensualité Novembre / نوفمبر	5000	0	5000	2026-11-05	0
14	2	1	Month_12	Mensualité Décembre / ديسمبر	5000	0	5000	2026-12-05	0
15	2	1	Month_1	Mensualité Janvier / يناير	5000	0	5000	2027-01-05	0
16	2	1	Month_2	Mensualité Février / فبراير	6250	0	6250	2027-02-05	0
17	2	1	Month_3	Mensualité Mars / مارس	6250	0	6250	2027-03-05	0
18	2	1	Month_4	Mensualité Avril / أبريل	6250	0	6250	2027-04-05	0
19	2	1	Month_5	Mensualité Mai / مايو	6250	0	6250	2027-05-05	0
20	2	1	Month_6	Mensualité Juin / يونيو	0	0	0	2027-06-05	0
1	1	1	Registration	Frais d'inscription	1500	0	1500	2026-04-07	1
21	3	1	Registration	Frais d'inscription	1500	0	1500	2026-04-26	0
22	3	1	Month_10	Mensualité Octobre / أكتوبر	5000	0	5000	2026-10-05	0
23	3	1	Month_11	Mensualité Novembre / نوفمبر	5000	0	5000	2026-11-05	0
24	3	1	Month_12	Mensualité Décembre / ديسمبر	5000	0	5000	2026-12-05	0
25	3	1	Month_1	Mensualité Janvier / يناير	5000	0	5000	2027-01-05	0
26	3	1	Month_2	Mensualité Février / فبراير	6250	0	6250	2027-02-05	0
27	3	1	Month_3	Mensualité Mars / مارس	6250	0	6250	2027-03-05	0
28	3	1	Month_4	Mensualité Avril / أبريل	6250	0	6250	2027-04-05	0
29	3	1	Month_5	Mensualité Mai / مايو	6250	0	6250	2027-05-05	0
30	3	1	Month_6	Mensualité Juin / يونيو	0	0	0	2027-06-05	0
\.


--
-- Data for Name: students; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.students (id, first_name_fr, last_name_fr, first_name_ar, last_name_ar, birth_date, birth_place, gender, address, parent_name, parent_phone, parent_email, parent_address, registration_date, status, photo_path, parent_pin, school_id, student_code, parent_pin_hash) FROM stdin;
1	Malick	Diouf	مالك	جوف	2020-04-04	Boune	M	Boune	Issa Thiaw	77 042 92 05	malikdiouf868@gmail.com	Mboul	2026-04-04	Active	school_data/photos/student_1_1775599350.4276.jpg	\N	1	EMG-0001	$2b$10$xWRMAavj9dby8yZTdUHDf.WujdQkRHfGFztvJDGapTPv.YkO2b7OS
2	Babou	Diop			2020-04-06	Mboul	M	Mboul			malikdiouf868@gmail.com		2026-04-06	Active	\N	\N	1	EMG-0002	$2b$10$MwLe1nXMCyoW3l7Prr8xNOvYaU9kPEdkH3YdjGFWTL16DGy1yWz2q
3	Loukhman	Diouf	لقمان	جوف	2020-04-26	Mboul	M	Boune	Chaiba Diouf	77 000 88 99	loukh@gimail.com	Boune	2026-04-26	Active	school_data/photos/student_1777200705.682989.jpg	\N	1	EMG-0003	$2b$10$.Hiheo1g/jUpVWbFqTkUGuNxi7kgyhg5NbPvUUX1oTwy7hr7d9Iam
\.


--
-- Data for Name: subjects; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.subjects (id, cycle_id, subject_name_ar, subject_name_fr, coefficient, subject_lang) FROM stdin;
1	1	قرآن	Quran	2	Arabe
2	1	توحيد	Tawhid	1	Arabe
\.


--
-- Data for Name: timetable; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.timetable (id, class_id, day_of_week, start_time, end_time, subject_id, teacher_id, room) FROM stdin;
1	1	Lundi	08:00	10:00	1	1	\N
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.users (id, staff_id, username, email, password_hash, role, status, created_date) FROM stdin;
1	\N	admin	admin@school.local	$2b$12$HObFSnvl71bXW0dd0aGA3..D9g30IwZpWtLqmX2JVZ3BoQEmvpz36	Admin	Actif	2026-04-04 00:26:50.481467
\.


--
-- Name: academicperiods_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.academicperiods_id_seq', 6, true);


--
-- Name: academicyears_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.academicyears_id_seq', 2, true);


--
-- Name: assessmenttypes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.assessmenttypes_id_seq', 6, true);


--
-- Name: auditlogs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.auditlogs_id_seq', 18, true);


--
-- Name: classes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.classes_id_seq', 1, true);


--
-- Name: cycles_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.cycles_id_seq', 1, true);


--
-- Name: emailsettings_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.emailsettings_id_seq', 3, true);


--
-- Name: expenses_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.expenses_id_seq', 2, true);


--
-- Name: grades_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.grades_id_seq', 5, true);


--
-- Name: inventoryitems_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.inventoryitems_id_seq', 1, true);


--
-- Name: inventorylog_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.inventorylog_id_seq', 2, true);


--
-- Name: monthlyfeeschedule_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.monthlyfeeschedule_id_seq', 18, true);


--
-- Name: monthlypaymentsstatus_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.monthlypaymentsstatus_id_seq', 1, true);


--
-- Name: notificationlogs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.notificationlogs_id_seq', 6, true);


--
-- Name: payments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.payments_id_seq', 1, true);


--
-- Name: registrationfees_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.registrationfees_id_seq', 1, true);


--
-- Name: salaryslips_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.salaryslips_id_seq', 1, true);


--
-- Name: schoolinfo_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.schoolinfo_id_seq', 3, true);


--
-- Name: schools_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.schools_id_seq', 1, false);


--
-- Name: staff_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.staff_id_seq', 1, true);


--
-- Name: staffattendance_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.staffattendance_id_seq', 2, true);


--
-- Name: staffleaves_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.staffleaves_id_seq', 2, true);


--
-- Name: studentattendance_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.studentattendance_id_seq', 5, true);


--
-- Name: studentclassnumbers_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.studentclassnumbers_id_seq', 6, true);


--
-- Name: studentdiscipline_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.studentdiscipline_id_seq', 2, true);


--
-- Name: studentdues_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.studentdues_id_seq', 30, true);


--
-- Name: students_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.students_id_seq', 3, true);


--
-- Name: subjects_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.subjects_id_seq', 2, true);


--
-- Name: timetable_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.timetable_id_seq', 1, true);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.users_id_seq', 2, true);


--
-- Name: academicperiods academicperiods_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.academicperiods
    ADD CONSTRAINT academicperiods_pkey PRIMARY KEY (id);


--
-- Name: academicyears academicyears_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.academicyears
    ADD CONSTRAINT academicyears_pkey PRIMARY KEY (id);


--
-- Name: academicyears academicyears_year_label_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.academicyears
    ADD CONSTRAINT academicyears_year_label_key UNIQUE (year_label);


--
-- Name: assessmenttypes assessmenttypes_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.assessmenttypes
    ADD CONSTRAINT assessmenttypes_pkey PRIMARY KEY (id);


--
-- Name: auditlogs auditlogs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auditlogs
    ADD CONSTRAINT auditlogs_pkey PRIMARY KEY (id);


--
-- Name: classes classes_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.classes
    ADD CONSTRAINT classes_pkey PRIMARY KEY (id);


--
-- Name: cycles cycles_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.cycles
    ADD CONSTRAINT cycles_pkey PRIMARY KEY (id);


--
-- Name: emailsettings emailsettings_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.emailsettings
    ADD CONSTRAINT emailsettings_pkey PRIMARY KEY (id);


--
-- Name: expenses expenses_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.expenses
    ADD CONSTRAINT expenses_pkey PRIMARY KEY (id);


--
-- Name: grades grades_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.grades
    ADD CONSTRAINT grades_pkey PRIMARY KEY (id);


--
-- Name: inventoryitems inventoryitems_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.inventoryitems
    ADD CONSTRAINT inventoryitems_pkey PRIMARY KEY (id);


--
-- Name: inventorylog inventorylog_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.inventorylog
    ADD CONSTRAINT inventorylog_pkey PRIMARY KEY (id);


--
-- Name: monthlyfeeschedule monthlyfeeschedule_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.monthlyfeeschedule
    ADD CONSTRAINT monthlyfeeschedule_pkey PRIMARY KEY (id);


--
-- Name: monthlypaymentsstatus monthlypaymentsstatus_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.monthlypaymentsstatus
    ADD CONSTRAINT monthlypaymentsstatus_pkey PRIMARY KEY (id);


--
-- Name: notificationlogs notificationlogs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.notificationlogs
    ADD CONSTRAINT notificationlogs_pkey PRIMARY KEY (id);


--
-- Name: payments payments_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_pkey PRIMARY KEY (id);


--
-- Name: registrationfees registrationfees_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.registrationfees
    ADD CONSTRAINT registrationfees_pkey PRIMARY KEY (id);


--
-- Name: salaryslips salaryslips_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.salaryslips
    ADD CONSTRAINT salaryslips_pkey PRIMARY KEY (id);


--
-- Name: schoolinfo schoolinfo_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.schoolinfo
    ADD CONSTRAINT schoolinfo_pkey PRIMARY KEY (id);


--
-- Name: schools schools_code_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.schools
    ADD CONSTRAINT schools_code_key UNIQUE (code);


--
-- Name: schools schools_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.schools
    ADD CONSTRAINT schools_name_key UNIQUE (name);


--
-- Name: schools schools_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.schools
    ADD CONSTRAINT schools_pkey PRIMARY KEY (id);


--
-- Name: staff staff_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.staff
    ADD CONSTRAINT staff_pkey PRIMARY KEY (id);


--
-- Name: staffattendance staffattendance_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.staffattendance
    ADD CONSTRAINT staffattendance_pkey PRIMARY KEY (id);


--
-- Name: staffleaves staffleaves_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.staffleaves
    ADD CONSTRAINT staffleaves_pkey PRIMARY KEY (id);


--
-- Name: studentattendance studentattendance_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.studentattendance
    ADD CONSTRAINT studentattendance_pkey PRIMARY KEY (id);


--
-- Name: studentclassnumbers studentclassnumbers_class_id_year_id_class_number_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.studentclassnumbers
    ADD CONSTRAINT studentclassnumbers_class_id_year_id_class_number_key UNIQUE (class_id, year_id, class_number);


--
-- Name: studentclassnumbers studentclassnumbers_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.studentclassnumbers
    ADD CONSTRAINT studentclassnumbers_pkey PRIMARY KEY (id);


--
-- Name: studentclassnumbers studentclassnumbers_student_id_year_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.studentclassnumbers
    ADD CONSTRAINT studentclassnumbers_student_id_year_id_key UNIQUE (student_id, year_id);


--
-- Name: studentdiscipline studentdiscipline_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.studentdiscipline
    ADD CONSTRAINT studentdiscipline_pkey PRIMARY KEY (id);


--
-- Name: studentdues studentdues_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.studentdues
    ADD CONSTRAINT studentdues_pkey PRIMARY KEY (id);


--
-- Name: students students_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.students
    ADD CONSTRAINT students_pkey PRIMARY KEY (id);


--
-- Name: subjects subjects_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.subjects
    ADD CONSTRAINT subjects_pkey PRIMARY KEY (id);


--
-- Name: timetable timetable_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.timetable
    ADD CONSTRAINT timetable_pkey PRIMARY KEY (id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: users users_username_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_username_key UNIQUE (username);


--
-- Name: idx_academic_periods_year_cycle_sort; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_academic_periods_year_cycle_sort ON public.academicperiods USING btree (year_id, cycle_id, sort_order);


--
-- Name: idx_assessment_period; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_assessment_period ON public.assessmenttypes USING btree (period_id);


--
-- Name: idx_attendance_student_year_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_attendance_student_year_status ON public.studentattendance USING btree (student_id, year_id, status);


--
-- Name: idx_attendance_year; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_attendance_year ON public.studentattendance USING btree (year_id);


--
-- Name: idx_attendance_year_period; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_attendance_year_period ON public.studentattendance USING btree (year_id, period_id);


--
-- Name: idx_classes_school; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_classes_school ON public.classes USING btree (school_id);


--
-- Name: idx_discipline_student_year; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_discipline_student_year ON public.studentdiscipline USING btree (student_id, year_id);


--
-- Name: idx_discipline_year; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_discipline_year ON public.studentdiscipline USING btree (year_id);


--
-- Name: idx_discipline_year_period; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_discipline_year_period ON public.studentdiscipline USING btree (year_id, period_id);


--
-- Name: idx_expenses_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_expenses_date ON public.expenses USING btree (expense_date);


--
-- Name: idx_grades_assessment; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_grades_assessment ON public.grades USING btree (assessment_id);


--
-- Name: idx_grades_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_grades_date ON public.grades USING btree (date_recorded);


--
-- Name: idx_grades_student_subject; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_grades_student_subject ON public.grades USING btree (student_id, subject_id);


--
-- Name: idx_grades_year; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_grades_year ON public.grades USING btree (year_id);


--
-- Name: idx_monthly_payments_due_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_monthly_payments_due_id ON public.monthlypaymentsstatus USING btree (due_id);


--
-- Name: idx_payments_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_payments_date ON public.payments USING btree (transaction_date);


--
-- Name: idx_payments_student; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_payments_student ON public.payments USING btree (student_id);


--
-- Name: idx_payments_student_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_payments_student_date ON public.payments USING btree (student_id, transaction_date);


--
-- Name: idx_staff_school; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_staff_school ON public.staff USING btree (school_id);


--
-- Name: idx_student_class_numbers_year_student; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_student_class_numbers_year_student ON public.studentclassnumbers USING btree (year_id, student_id);


--
-- Name: idx_student_dues_paid; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_student_dues_paid ON public.studentdues USING btree (is_paid);


--
-- Name: idx_student_dues_student_year; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_student_dues_student_year ON public.studentdues USING btree (student_id, year_id);


--
-- Name: idx_students_class_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_students_class_status ON public.students USING btree (status);


--
-- Name: idx_students_parent_pin; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_students_parent_pin ON public.students USING btree (parent_pin) WHERE (parent_pin IS NOT NULL);


--
-- Name: idx_students_school; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_students_school ON public.students USING btree (school_id);


--
-- Name: idx_students_student_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX idx_students_student_code ON public.students USING btree (student_code) WHERE (student_code IS NOT NULL);


--
-- Name: idx_years_school; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_years_school ON public.academicyears USING btree (school_id);


--
-- Name: academicperiods academicperiods_cycle_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.academicperiods
    ADD CONSTRAINT academicperiods_cycle_id_fkey FOREIGN KEY (cycle_id) REFERENCES public.cycles(id);


--
-- Name: academicperiods academicperiods_year_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.academicperiods
    ADD CONSTRAINT academicperiods_year_id_fkey FOREIGN KEY (year_id) REFERENCES public.academicyears(id);


--
-- Name: assessmenttypes assessmenttypes_period_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.assessmenttypes
    ADD CONSTRAINT assessmenttypes_period_id_fkey FOREIGN KEY (period_id) REFERENCES public.academicperiods(id);


--
-- Name: classes classes_cycle_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.classes
    ADD CONSTRAINT classes_cycle_id_fkey FOREIGN KEY (cycle_id) REFERENCES public.cycles(id) ON DELETE CASCADE;


--
-- Name: users fk_staff; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT fk_staff FOREIGN KEY (staff_id) REFERENCES public.staff(id) ON DELETE SET NULL;


--
-- Name: grades grades_assessment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.grades
    ADD CONSTRAINT grades_assessment_id_fkey FOREIGN KEY (assessment_id) REFERENCES public.assessmenttypes(id);


--
-- Name: grades grades_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.grades
    ADD CONSTRAINT grades_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.students(id) ON DELETE CASCADE;


--
-- Name: grades grades_subject_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.grades
    ADD CONSTRAINT grades_subject_id_fkey FOREIGN KEY (subject_id) REFERENCES public.subjects(id);


--
-- Name: grades grades_year_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.grades
    ADD CONSTRAINT grades_year_id_fkey FOREIGN KEY (year_id) REFERENCES public.academicyears(id);


--
-- Name: inventorylog inventorylog_item_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.inventorylog
    ADD CONSTRAINT inventorylog_item_id_fkey FOREIGN KEY (item_id) REFERENCES public.inventoryitems(id);


--
-- Name: monthlyfeeschedule monthlyfeeschedule_class_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.monthlyfeeschedule
    ADD CONSTRAINT monthlyfeeschedule_class_id_fkey FOREIGN KEY (class_id) REFERENCES public.classes(id);


--
-- Name: monthlypaymentsstatus monthlypaymentsstatus_due_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.monthlypaymentsstatus
    ADD CONSTRAINT monthlypaymentsstatus_due_id_fkey FOREIGN KEY (due_id) REFERENCES public.studentdues(id);


--
-- Name: monthlypaymentsstatus monthlypaymentsstatus_payment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.monthlypaymentsstatus
    ADD CONSTRAINT monthlypaymentsstatus_payment_id_fkey FOREIGN KEY (payment_id) REFERENCES public.payments(id);


--
-- Name: monthlypaymentsstatus monthlypaymentsstatus_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.monthlypaymentsstatus
    ADD CONSTRAINT monthlypaymentsstatus_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.students(id);


--
-- Name: payments payments_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.students(id) ON DELETE RESTRICT;


--
-- Name: payments payments_year_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_year_id_fkey FOREIGN KEY (year_id) REFERENCES public.academicyears(id);


--
-- Name: registrationfees registrationfees_class_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.registrationfees
    ADD CONSTRAINT registrationfees_class_id_fkey FOREIGN KEY (class_id) REFERENCES public.classes(id);


--
-- Name: salaryslips salaryslips_staff_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.salaryslips
    ADD CONSTRAINT salaryslips_staff_id_fkey FOREIGN KEY (staff_id) REFERENCES public.staff(id);


--
-- Name: staffattendance staffattendance_staff_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.staffattendance
    ADD CONSTRAINT staffattendance_staff_id_fkey FOREIGN KEY (staff_id) REFERENCES public.staff(id);


--
-- Name: staffleaves staffleaves_staff_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.staffleaves
    ADD CONSTRAINT staffleaves_staff_id_fkey FOREIGN KEY (staff_id) REFERENCES public.staff(id);


--
-- Name: studentattendance studentattendance_period_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.studentattendance
    ADD CONSTRAINT studentattendance_period_id_fkey FOREIGN KEY (period_id) REFERENCES public.academicperiods(id);


--
-- Name: studentattendance studentattendance_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.studentattendance
    ADD CONSTRAINT studentattendance_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.students(id) ON DELETE CASCADE;


--
-- Name: studentattendance studentattendance_year_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.studentattendance
    ADD CONSTRAINT studentattendance_year_id_fkey FOREIGN KEY (year_id) REFERENCES public.academicyears(id);


--
-- Name: studentclassnumbers studentclassnumbers_class_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.studentclassnumbers
    ADD CONSTRAINT studentclassnumbers_class_id_fkey FOREIGN KEY (class_id) REFERENCES public.classes(id);


--
-- Name: studentclassnumbers studentclassnumbers_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.studentclassnumbers
    ADD CONSTRAINT studentclassnumbers_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.students(id) ON DELETE CASCADE;


--
-- Name: studentclassnumbers studentclassnumbers_year_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.studentclassnumbers
    ADD CONSTRAINT studentclassnumbers_year_id_fkey FOREIGN KEY (year_id) REFERENCES public.academicyears(id);


--
-- Name: studentdiscipline studentdiscipline_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.studentdiscipline
    ADD CONSTRAINT studentdiscipline_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.students(id);


--
-- Name: studentdues studentdues_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.studentdues
    ADD CONSTRAINT studentdues_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.students(id);


--
-- Name: studentdues studentdues_year_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.studentdues
    ADD CONSTRAINT studentdues_year_id_fkey FOREIGN KEY (year_id) REFERENCES public.academicyears(id);


--
-- Name: subjects subjects_cycle_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.subjects
    ADD CONSTRAINT subjects_cycle_id_fkey FOREIGN KEY (cycle_id) REFERENCES public.cycles(id);


--
-- Name: timetable timetable_class_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.timetable
    ADD CONSTRAINT timetable_class_id_fkey FOREIGN KEY (class_id) REFERENCES public.classes(id);


--
-- Name: timetable timetable_subject_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.timetable
    ADD CONSTRAINT timetable_subject_id_fkey FOREIGN KEY (subject_id) REFERENCES public.subjects(id);


--
-- Name: timetable timetable_teacher_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.timetable
    ADD CONSTRAINT timetable_teacher_id_fkey FOREIGN KEY (teacher_id) REFERENCES public.staff(id);


--
-- PostgreSQL database dump complete
--

\unrestrict PipeJpBbM3IWXSfRVViFmmm7TSupJDCps9W1d98wUIYwOcVPErP66SVQNdPwyhR

