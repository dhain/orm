import unittest

from ..util import *

import orm.connection


class InvestorCompany(orm.model.Model):
    orm_table = 'investor_company'
    person_id = orm.model.Column()
    company_id = orm.model.Column()


class Person(orm.model.Model):
    orm_table = 'person'
    person_id = orm.model.Column()
    name = orm.model.Column()
    investments = orm.model.ManyToMany(
        person_id, InvestorCompany.person_id,
        InvestorCompany.company_id, 'Company.company_id'
    )


class Employee(Person):
    company_id = orm.model.Column()
    company = orm.model.ToOne(company_id, 'Company.company_id')


class Company(orm.model.Model):
    orm_table = 'company'
    company_id = orm.model.Column()
    name = orm.model.Column()
    employees = orm.model.ToMany(company_id, Employee.company_id)
    investors = orm.model.ManyToMany(
        company_id, InvestorCompany.company_id,
        InvestorCompany.person_id, Person.person_id
    )


class TestOrm(SqlTestCase):
    def setUp(self):
        self.db = orm.connection.connect(':memory:')
        cur = self.db.cursor()
        with self.db:
            cur.executescript(
                '''
                create table person (
                    person_id integer not null primary key autoincrement,
                    name text not null,
                    company_id integer
                );
                create table company (
                    company_id integer not null primary key autoincrement,
                    name text not null
                );
                create table investor_company (
                    person_id integer not null,
                    company_id integer not null
                );
                insert into company (company_id, name) values (1, 'Amazon.ca');
                insert into company (company_id, name) values (2, 'Google');
                insert into person (person_id, name) values (1, 'Guido');
                insert into person (person_id, name) values (2, 'Scott');
                insert into person (person_id, name, company_id)
                    values (3, 'Ramona', 1);
                insert into investor_company (person_id, company_id)
                    values (1, 2);  -- Guido, Google
                insert into investor_company (person_id, company_id)
                    values (2, 2);  -- Scott, Google
                insert into investor_company (person_id, company_id)
                    values (3, 1);  -- Ramona, Google
                insert into investor_company (person_id, company_id)
                    values (3, 2);  -- Ramona, Amazon.ca
                '''
            )

    def test_select_iter(self):
        q = orm.query.Select(sources=orm.query.Sql('person'))
        self.assertEqual(
            list(q),
            [
                (1, 'Guido', None),
                (2, 'Scott', None),
                (3, 'Ramona', 1),
            ]
        )

    def test_select_getitem_slice(self):
        q = orm.query.Select(sources=orm.query.Sql('person'))
        self.assertEqual(
            list(q[:1]),
            [
                (1, 'Guido', None),
            ]
        )

    def test_select_getitem_index(self):
        q = orm.query.Select(sources=orm.query.Sql('person'))
        self.assertEqual(q[1], (2, 'Scott', None))
        self.assertEqual(q[0], (1, 'Guido', None))

    def test_select_getitem_index_indexerror(self):
        q = orm.query.Select(sources=orm.query.Sql('person'))
        self.assertRaises(IndexError, q.__getitem__, 3)

    def test_delete(self):
        q = orm.query.Delete(orm.query.Sql('person'))
        with self.db:
            q.execute()
        cur = self.db.cursor()
        cur.execute('select count(*) from person')
        self.assertEqual(cur.fetchone()[0], 0)

    def test_insert(self):
        q = orm.query.Insert(
            orm.query.Sql('person'),
            orm.query.Sql('name'),
            orm.query.Expr('Knives')
        )
        with self.db:
            q.execute()
        cur = self.db.cursor()
        cur.execute('select * from person where name=?', ('Knives',))
        self.assertEqual(cur.fetchone(), (4, 'Knives', None))

    def test_model(self):
        scott = Person.find(Person.name == 'Scott')[0]
        self.assertTrue(isinstance(scott, Person))
        self.assertColumnEqual(scott.person_id, 2)
        self.assertColumnEqual(scott.name, 'Scott')

    def test_model_subclass(self):
        ramona = Employee.find(Employee.name == 'Ramona')[0]
        self.assertTrue(isinstance(ramona, Employee))
        self.assertColumnEqual(ramona.person_id, 3)
        self.assertColumnEqual(ramona.name, 'Ramona')
        self.assertColumnEqual(ramona.company_id, 1)

    def test_join(self):
        a1 = Person.as_alias('m1')
        a2 = Person.as_alias('m2')
        obj1, obj2 = orm.model.ModelSelect(
            a1.orm_columns + a2.orm_columns,
            orm.query.ExprList([a1, a2]),
            a1.person_id == a2.person_id
        ).order_by(a1.person_id)[0]
        for obj in (obj1, obj2):
            self.assertTrue(isinstance(obj, Person))
            self.assertColumnEqual(obj.person_id, 1)
            self.assertColumnEqual(obj.name, 'Guido')

    def test_to_one(self):
        ramona = Employee.find(Employee.name == 'Ramona')[0]
        amazon = ramona.company
        self.assertTrue(isinstance(amazon, Company))
        self.assertColumnEqual(amazon.name, 'Amazon.ca')

    def test_to_one_not_found(self):
        scott = Employee.find(Employee.name == 'Scott')[0]
        bogus = scott.company
        self.assertTrue(bogus is None)

    def test_to_many(self):
        amazon = Company.find(Company.name == 'Amazon.ca')[0]
        employees = amazon.employees
        self.assertTrue(isinstance(employees, orm.model.ModelSelect))
        self.assertEqual(len(employees), 1)
        ramona = employees.order_by(Employee.person_id)[0]
        self.assertTrue(isinstance(ramona, Employee))
        self.assertColumnEqual(ramona.name, 'Ramona')

    def test_many_to_many(self):
        google = Company.find(Company.name == 'Google')[0]
        investors = google.investors
        self.assertTrue(isinstance(investors, orm.model.ModelSelect))
        self.assertEqual(len(investors), 3)
        guido = google.investors.order_by(Person.person_id)[0]
        self.assertTrue(isinstance(guido, Person))
        self.assertColumnEqual(guido.name, 'Guido')


if __name__ == "__main__":
    main(__name__)
