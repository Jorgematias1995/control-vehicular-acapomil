-- =====================================================================
-- 02_datos.sql · Datos base del proyecto del profesor (Sesión 12)
-- 30 conductores · 15 vehículos · 18 autorizaciones
-- El proyecto del profesor YA los tiene; sirve para recrear la base en
-- otro proyecto, después de 01_esquema.sql. Re-ejecutable: no duplica filas.
-- =====================================================================

insert into public.conductores (rut, nombre_completo, grado_o_cargo, unidad_destino, estado) values
  ('18.234.567-K', 'Carlos Soto Ramírez', 'Capitán', 'Batallón Logístico N°1', 'Activo'),
  ('17.987.654-3', 'Alejandro Morales Rojas', 'Teniente', 'Compañía de Telecomunicaciones', 'Activo'),
  ('19.111.222-4', 'Matías Valenzuela Pérez', 'Subteniente', 'Escuadrón de Reconocimiento', 'Activo'),
  ('16.555.444-2', 'Juan Pablo Henríquez', 'Sargento 1°', 'Plana Mayor', 'Activo'),
  ('15.444.333-1', 'Esteban Fuentes Garrido', 'Sargento 2°', 'Batallón Logístico N°1', 'Activo'),
  ('20.123.456-8', 'Ignacio Alarcón Soto', 'Cabo 1°', 'Sección de Transporte', 'Activo'),
  ('18.888.999-5', 'Rodrigo Pérez Silva', 'Cabo 2°', 'Sección de Transporte', 'Activo'),
  ('14.222.111-9', 'Héctor Gómez Medina', 'Suboficial', 'Parque de Material de Guerra', 'Activo'),
  ('19.555.666-7', 'Felipe Cárdenas Díaz', 'Soldado Conscripto', 'Batallón Logístico N°1', 'Activo'),
  ('20.444.333-6', 'Diego Morales Vega', 'Soldado Conscripto', 'Batallón Logístico N°1', 'Activo'),
  ('17.333.222-0', 'Mauricio Silva Contreras', 'Capitán', 'DIVEDUC', 'Activo'),
  ('16.111.999-8', 'Cristian Vergara Lagos', 'Mayor', 'ACAPOMIL', 'Activo'),
  ('15.888.777-4', 'Patricio Rojas Aravena', 'Teniente Coronel', 'ACAPOMIL', 'Activo'),
  ('19.999.888-1', 'Vicente Araya Bustos', 'Subteniente', 'Compañía de Policial Militar', 'Activo'),
  ('21.000.111-2', 'Benjamín Muñoz Saavedra', 'Cabo 2°', 'Compañía de Policial Militar', 'Activo'),
  ('18.456.789-1', 'Gonzalo Espinoza Riquelme', 'Sargento 2°', 'Sección de Transporte', 'Activo'),
  ('17.123.987-5', 'Fabián Torres Neira', 'Cabo 1°', 'Sección de Transporte', 'Activo'),
  ('16.789.123-4', 'Daniela Soto Mardones', 'Teniente', 'Servicio de Sanidad', 'Activo'),
  ('20.555.123-9', 'Valentina Rojas Montero', 'Subteniente', 'Servicio de Sanidad', 'Activo'),
  ('19.333.444-5', 'Sebastián Pizarro Bravo', 'Cabo 2°', 'Batallón Logístico N°1', 'Activo'),
  ('15.222.333-8', 'Francisco Molina Jorquera', 'Suboficial Mayor', 'Plana Mayor', 'Activo'),
  ('18.666.777-2', 'Lucas Navarrete Espinoza', 'Cabo 1°', 'Parque de Material de Guerra', 'Activo'),
  ('17.444.555-6', 'Ernesto Castillo Palma', 'Sargento 1°', 'Compañía de Telecomunicaciones', 'Activo'),
  ('16.222.888-3', 'Manuel Reyes Albornoz', 'Mayor', 'Escuadrón de Reconocimiento', 'Activo'),
  ('21.111.222-9', 'Joaquín Contreras Osses', 'Soldado Conscripto', 'Sección de Transporte', 'Activo'),
  ('20.888.777-1', 'Agustín Parra Valdés', 'Soldado Conscripto', 'Sección de Transporte', 'Activo'),
  ('19.777.666-4', 'Nicolás Jorquera Salinas', 'Cabo 2°', 'Compañía de Policial Militar', 'Activo'),
  ('18.111.333-7', 'Claudio Donoso Pardo', 'Sargento 2°', 'Batallón Logístico N°1', 'Activo'),
  ('14.999.555-0', 'Pedro Pablo Ibáñez', 'Coronel', 'Dirección Superior', 'Activo'),
  ('17.666.444-9', 'Ricardo Meléndez Zúñiga', 'Capitán', 'DIVEDUC', 'Activo')
on conflict (rut) do nothing;

insert into public.vehiculos (patente, tipo_vehiculo, marca_modelo, anio, kilometraje_actual, estado_operativo) values
  ('ABCD-12', 'Vehículo Táctico', 'Mowag Piranha III', 2018, 45200, 'Operativo'),
  ('EFGH-34', 'Camión Logístico', 'Mercedes-Benz Atego', 2020, 31000, 'Operativo'),
  ('JKLM-56', 'SUV Institucional', 'Toyota Land Cruiser Prado', 2022, 18500, 'Operativo'),
  ('NPQR-78', 'Camioneta 4x4', 'Mitsubishi L200 Katana', 2023, 12400, 'Operativo'),
  ('STUV-90', 'Camioneta 4x4', 'Nissan Navara D23', 2021, 54000, 'Requiere Mantención'),
  ('WXYZ-11', 'Minibus de Personal', 'Hyundai H1 / Staria', 2019, 68900, 'Operativo'),
  ('BBCC-22', 'Vehículo Táctico', 'Humvee HMMWV', 2015, 89200, 'Requiere Mantención'),
  ('DDEE-33', 'Camión Aljibe', 'Freightliner M2', 2017, 76000, 'Crítico'),
  ('FFGG-44', 'Automóvil de Enlace', 'Chevrolet Sail', 2022, 24100, 'Operativo'),
  ('HHII-56', 'Automóvil de Enlace', 'Kia Rio 5', 2021, 41200, 'Operativo'),
  ('JJKK-78', 'SUV Institucional', 'Toyota RAV4', 2023, 9500, 'Operativo'),
  ('LLMM-90', 'Camión de Carga', 'JAC Gallop Heavy Duty', 2020, 52300, 'Operativo'),
  ('NNPP-12', 'Minibus de Personal', 'Toyota Hiace', 2022, 19800, 'Operativo'),
  ('RRSS-34', 'Camioneta 4x4', 'Ford Ranger 4x4', 2022, 27600, 'Operativo'),
  ('TTWW-56', 'Vehículo Especial', 'Polaris Ranger RZR (Reconocimiento)', 2023, 4200, 'Operativo')
on conflict (patente) do nothing;

insert into public.autorizaciones (patente, rut_conductor, fecha_asignacion, vigente)
select v.patente, v.rut, v.fecha::timestamptz, v.vigente
from (values
  ('ABCD-12', '18.234.567-K', '2026-11-11T22:28:16.182039+00:00', true),
  ('EFGH-34', '15.444.333-1', '2026-11-11T22:28:16.182039+00:00', true),
  ('JKLM-56', '16.111.999-8', '2026-11-11T22:28:16.182039+00:00', true),
  ('NPQR-78', '17.987.654-3', '2026-11-11T22:28:16.182039+00:00', true),
  ('STUV-90', '20.123.456-8', '2026-11-11T22:28:16.182039+00:00', true),
  ('WXYZ-11', '14.222.111-9', '2026-11-11T22:28:16.182039+00:00', true),
  ('BBCC-22', '18.888.999-5', '2026-11-11T22:28:16.182039+00:00', true),
  ('DDEE-33', '19.555.666-7', '2026-11-11T22:28:16.182039+00:00', true),
  ('FFGG-44', '17.333.222-0', '2026-11-11T22:28:16.182039+00:00', true),
  ('HHII-56', '15.888.777-4', '2026-11-11T22:28:16.182039+00:00', true),
  ('JJKK-78', '16.789.123-4', '2026-11-11T22:28:16.182039+00:00', true),
  ('LLMM-90', '18.456.789-1', '2026-11-11T22:28:16.182039+00:00', true),
  ('NNPP-12', '17.123.987-5', '2026-11-11T22:28:16.182039+00:00', true),
  ('RRSS-34', '19.333.444-5', '2026-11-11T22:28:16.182039+00:00', true),
  ('TTWW-56', '19.111.222-4', '2026-11-11T22:28:16.182039+00:00', true),
  ('ABCD-12', '16.222.888-3', '2026-11-11T22:28:16.182039+00:00', true),
  ('NPQR-78', '18.234.567-K', '2026-11-11T22:28:16.182039+00:00', true),
  ('JKLM-56', '15.888.777-4', '2026-11-11T22:28:16.182039+00:00', true)
) as v(patente, rut, fecha, vigente)
where not exists (select 1 from public.autorizaciones a
                  where a.patente = v.patente and a.rut_conductor = v.rut);
