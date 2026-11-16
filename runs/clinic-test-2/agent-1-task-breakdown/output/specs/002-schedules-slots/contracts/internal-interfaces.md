# Internal interfaces (in-process, inside ctr-clinic-api)

## Provided by cmp-scheduling to cmp-booking and cmp-reception

Module `app/scheduling/services/slots.py`:

| Function | Purpose |
|---|---|
| `find_free_slots(clinic_id, treatment_type_id, from_date, to_date, dentist_id=None, now=None, for_patient=False) -> list[FreeSlot]` | The same calculation as `GET /clinics/{id}/slots`. |
| `first_available(clinic_id, treatment_type_id, limit=10, now=None, for_patient=False) -> list[FreeSlot]` | The 10 earliest slots across the clinic's dentists. |
| `is_slot_free(clinic_id, dentist_id, treatment_type_id, start_at_utc, exclude_appointment_id=None) -> bool` | Used by booking before insert (the database exclusion constraint of ADR-0003 stays the final guard). `exclude_appointment_id` lets a reschedule ignore the appointment being moved. |
| `get_treatment_type(treatment_type_id) -> TreatmentType` | Duration and online flag for booking. |

## Required from cmp-booking (feature 003/005)

Module `app/scheduling/ports.py`:

```python
class AppointmentReader(Protocol):
    def list_active(self, dentist_ids: Sequence[int], start_utc: datetime, end_utc: datetime,
                    clinic_id: int | None = None) -> list[AppointmentBrief]: ...
```

`AppointmentBrief`: `id, clinic_id, dentist_id, start_utc, end_utc, treatment_name, patient_name, patient_phone`. Returns appointments with status booked that overlap `[start_utc, end_utc)`, at every clinic when `clinic_id` is None. Read only. The patient fields are used only by the "to move" list and are never logged.

Registration: cmp-booking sets the reader with `app.scheduling.ports.register_appointment_reader(reader)` at start-up; until then a reader that returns no appointments is used.
