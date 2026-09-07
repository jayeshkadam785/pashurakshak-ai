# ============================================================
# DISTRICT OFFICER DASHBOARD
# ============================================================

@app.route("/dashboard/district")
def dashboard_district():

    district_name = (
        request.args.get("district", "Satara").strip()
        or "Satara"
    )

    reports = get_reports()

    # --------------------------------------------------------
    # LOAD ANIMALS
    # --------------------------------------------------------

    if supabase:

        try:

            animal_response = (
                supabase
                .table("animals")
                .select("*")
                .limit(5000)
                .execute()
            )

            animals = animal_response.data or []

        except Exception as exc:

            print(
                "District animal dashboard error:",
                repr(exc)
            )

            animals = []

    else:

        animals = list(
            _MEMORY_ANIMALS
        )

    # --------------------------------------------------------
    # LOAD VACCINATION RECORDS
    # --------------------------------------------------------

    vaccinations = []

    if supabase:

        try:

            vaccination_response = (
                supabase
                .table("vaccination_records")
                .select("*")
                .limit(5000)
                .execute()
            )

            vaccinations = (
                vaccination_response.data
                or []
            )

        except Exception as exc:

            print(
                "District vaccination dashboard error:",
                repr(exc)
            )

    # --------------------------------------------------------
    # HELPERS
    # --------------------------------------------------------

    def clean(value, default="Unknown"):

        value = str(
            value or ""
        ).strip()

        return (
            value
            if value
            else default
        )

    def report_status(report):

        return str(
            report.get("case_status")
            or report.get("status")
            or "OPEN"
        ).upper()

    def report_risk(report):

        return str(
            report.get("risk_level")
            or "LOW"
        ).upper()

    def vaccinated_status(value):

        return str(
            value or ""
        ).strip().upper() in {
            "VACCINATED",
            "UP_TO_DATE",
            "COMPLETED",
            "COMPLETE",
            "FULLY_VACCINATED",
            "YES"
        }

    def death_report(report):

        symptoms = normalize_symptoms(
            report.get(
                "symptoms",
                []
            )
        )

        status = report_status(
            report
        )

        return (
            "death" in symptoms
            or "deaths" in symptoms
            or status in {
                "DEATH",
                "DECEASED",
                "DIED"
            }
        )

    # --------------------------------------------------------
    # ANIMAL LOOKUP
    # --------------------------------------------------------

    animal_map = {}

    for animal in animals:

        animal_id = animal.get(
            "id"
        )

        if animal_id is not None:

            animal_map[
                str(animal_id)
            ] = animal

    # --------------------------------------------------------
    # DATA STRUCTURES
    # --------------------------------------------------------

    village_data = {}
    block_data = {}

    def ensure_village(
        village,
        block
    ):

        if village not in village_data:

            village_data[village] = {

                "village":
                    village,

                "block":
                    block,

                "animals":
                    0,

                "vaccinated_animals":
                    0,

                "vaccinated_ids":
                    set(),

                "active_cases":
                    0,

                "high_risk":
                    0,

                "deaths":
                    0,

                "report_count":
                    0,

                "affected_animals":
                    0
            }

    def ensure_block(block):

        if block not in block_data:

            block_data[block] = {

                "block":
                    block,

                "villages":
                    set(),

                "animals":
                    0,

                "vaccinated_animals":
                    0,

                "vaccinated_ids":
                    set(),

                "active_cases":
                    0,

                "high_risk":
                    0,

                "deaths":
                    0,

                "report_count":
                    0,

                "affected_animals":
                    0
            }

    # --------------------------------------------------------
    # PROCESS ANIMAL REGISTRY
    # --------------------------------------------------------

    for animal in animals:

        village = clean(
            animal.get("village")
        )

        block = clean(
            animal.get("block")
        )

        ensure_village(
            village,
            block
        )

        ensure_block(
            block
        )

        village_data[
            village
        ][
            "animals"
        ] += 1

        block_data[
            block
        ][
            "animals"
        ] += 1

        block_data[
            block
        ][
            "villages"
        ].add(
            village
        )

        # Existing animal vaccination status
        if vaccinated_status(
            animal.get(
                "vaccination_status"
            )
        ):

            village_data[
                village
            ][
                "vaccinated_animals"
            ] += 1

            block_data[
                block
            ][
                "vaccinated_animals"
            ] += 1

            if animal.get("id") is not None:

                animal_id = str(
                    animal.get("id")
                )

                village_data[
                    village
                ][
                    "vaccinated_ids"
                ].add(
                    animal_id
                )

                block_data[
                    block
                ][
                    "vaccinated_ids"
                ].add(
                    animal_id
                )

    # --------------------------------------------------------
    # PROCESS VACCINATION RECORDS
    # --------------------------------------------------------

    for vaccination in vaccinations:

        animal_id = vaccination.get(
            "animal_id"
        )

        if animal_id is None:
            continue

        animal = animal_map.get(
            str(animal_id)
        )

        if not animal:
            continue

        village = clean(
            animal.get("village")
        )

        block = clean(
            animal.get("block")
        )

        ensure_village(
            village,
            block
        )

        ensure_block(
            block
        )

        block_data[
            block
        ][
            "villages"
        ].add(
            village
        )

        animal_key = str(
            animal.get("id")
        )

        # Count unique animals only once
        if animal_key not in village_data[
            village
        ][
            "vaccinated_ids"
        ]:

            village_data[
                village
            ][
                "vaccinated_ids"
            ].add(
                animal_key
            )

            village_data[
                village
            ][
                "vaccinated_animals"
            ] += 1

        if animal_key not in block_data[
            block
        ][
            "vaccinated_ids"
        ]:

            block_data[
                block
            ][
                "vaccinated_ids"
            ].add(
                animal_key
            )

            block_data[
                block
            ][
                "vaccinated_animals"
            ] += 1

    # --------------------------------------------------------
    # PROCESS DISEASE REPORTS
    # --------------------------------------------------------

    total_active_cases = 0
    total_high_risk = 0
    total_deaths = 0

    outbreak_villages = set()

    village_high_risk_counts = {}

    for report in reports:

        village = clean(
            report.get("village")
        )

        block = clean(
            report.get("block")
        )

        ensure_village(
            village,
            block
        )

        ensure_block(
            block
        )

        block_data[
            block
        ][
            "villages"
        ].add(
            village
        )

        risk = report_risk(
            report
        )

        status = report_status(
            report
        )

        affected_count = max(
            safe_int(
                report.get(
                    "affected_count"
                ),
                1
            ),
            1
        )

        # ----------------------------------------------------
        # REPORT COUNT
        # ----------------------------------------------------

        village_data[
            village
        ][
            "report_count"
        ] += 1

        block_data[
            block
        ][
            "report_count"
        ] += 1

        # ----------------------------------------------------
        # AFFECTED ANIMALS
        # ----------------------------------------------------

        village_data[
            village
        ][
            "affected_animals"
        ] += affected_count

        block_data[
            block
        ][
            "affected_animals"
        ] += affected_count

        # ----------------------------------------------------
        # ACTIVE CASE
        # ----------------------------------------------------

        if status not in {
            "CLOSED",
            "REJECTED",
            "RESOLVED"
        }:

            village_data[
                village
            ][
                "active_cases"
            ] += 1

            block_data[
                block
            ][
                "active_cases"
            ] += 1

            total_active_cases += 1

        # ----------------------------------------------------
        # HIGH RISK
        # ----------------------------------------------------

        if risk == "HIGH":

            village_data[
                village
            ][
                "high_risk"
            ] += 1

            block_data[
                block
            ][
                "high_risk"
            ] += 1

            total_high_risk += 1

            village_high_risk_counts[
                village
            ] = (
                village_high_risk_counts.get(
                    village,
                    0
                ) + 1
            )

        # ----------------------------------------------------
        # DEATH
        # ----------------------------------------------------

        if death_report(report):

            village_data[
                village
            ][
                "deaths"
            ] += affected_count

            block_data[
                block
            ][
                "deaths"
            ] += affected_count

            total_deaths += affected_count

        # ----------------------------------------------------
        # OUTBREAK SIGNAL
        # ----------------------------------------------------

        if (
            risk == "HIGH"
            and (
                affected_count >= 5
                or village_high_risk_counts.get(
                    village,
                    0
                ) >= 2
                or village_data[
                    village
                ][
                    "report_count"
                ] >= 3
            )
        ):

            outbreak_villages.add(
                village
            )

    # --------------------------------------------------------
    # VILLAGE SUMMARY
    # --------------------------------------------------------

    villages = []

    for village in village_data.values():

        high_risk = village[
            "high_risk"
        ]

        active_cases = village[
            "active_cases"
        ]

        deaths = village[
            "deaths"
        ]

        animals_count = village[
            "animals"
        ]

        vaccinated_count = village[
            "vaccinated_animals"
        ]

        # ----------------------------------------------------
        # VILLAGE RISK
        # ----------------------------------------------------

        if (
            high_risk >= 3
            or deaths >= 3
        ):

            risk = "HIGH"

        elif (
            high_risk >= 1
            or active_cases >= 3
            or deaths >= 1
        ):

            risk = "WATCH"

        else:

            risk = "LOW"

        # ----------------------------------------------------
        # VACCINATION COVERAGE
        # ----------------------------------------------------

        if animals_count > 0:

            vaccination_coverage = min(
                100,
                round(
                    (
                        vaccinated_count
                        / animals_count
                    ) * 100
                )
            )

        else:

            vaccination_coverage = 0

        villages.append({

            "village":
                village["village"],

            "block":
                village["block"],

            "animals":
                animals_count,

            "vaccinated_animals":
                vaccinated_count,

            "vaccination_coverage":
                vaccination_coverage,

            "active_cases":
                active_cases,

            "high_risk":
                high_risk,

            "deaths":
                deaths,

            "report_count":
                village["report_count"],

            "affected_animals":
                village[
                    "affected_animals"
                ],

            "risk":
                risk
        })

    villages.sort(
        key=lambda item: (
            item["risk"] == "HIGH",
            item["high_risk"],
            item["active_cases"],
            item["deaths"]
        ),
        reverse=True
    )

    # --------------------------------------------------------
    # BLOCK SUMMARY
    # --------------------------------------------------------

    blocks = []

    for block in block_data.values():

        animals_count = block[
            "animals"
        ]

        vaccinated_count = block[
            "vaccinated_animals"
        ]

        if animals_count > 0:

            vaccination_coverage = min(
                100,
                round(
                    (
                        vaccinated_count
                        / animals_count
                    ) * 100
                )
            )

        else:

            vaccination_coverage = 0

        if (
            block["high_risk"] >= 3
            or block["deaths"] >= 3
        ):

            risk = "HIGH"

        elif (
            block["high_risk"] >= 1
            or block["active_cases"] >= 3
            or block["deaths"] >= 1
        ):

            risk = "WATCH"

        else:

            risk = "LOW"

        blocks.append({

            "block":
                block["block"],

            "villages":
                len(
                    block["villages"]
                ),

            "animals":
                animals_count,

            "vaccinated_animals":
                vaccinated_count,

            "vaccination_coverage":
                vaccination_coverage,

            "active_cases":
                block[
                    "active_cases"
                ],

            "high_risk":
                block[
                    "high_risk"
                ],

            "deaths":
                block[
                    "deaths"
                ],

            "report_count":
                block[
                    "report_count"
                ],

            "affected_animals":
                block[
                    "affected_animals"
                ],

            "risk":
                risk
        })

    blocks.sort(
        key=lambda item: (
            item["risk"] == "HIGH",
            item["high_risk"],
            item["active_cases"],
            item["deaths"]
        ),
        reverse=True
    )

    # --------------------------------------------------------
    # DISTRICT VACCINATION
    # --------------------------------------------------------

    vaccinated_animal_ids = set()

    for animal in animals:

        if vaccinated_status(
            animal.get(
                "vaccination_status"
            )
        ):

            if animal.get("id") is not None:

                vaccinated_animal_ids.add(
                    str(
                        animal.get("id")
                    )
                )

    for vaccination in vaccinations:

        animal_id = vaccination.get(
            "animal_id"
        )

        if animal_id is not None:

            if str(animal_id) in animal_map:

                vaccinated_animal_ids.add(
                    str(animal_id)
                )

    total_animals = len(
        animals
    )

    vaccinated_animals = len(
        vaccinated_animal_ids
    )

    if total_animals > 0:

        vaccination_coverage = min(
            100,
            round(
                (
                    vaccinated_animals
                    / total_animals
                ) * 100
            )
        )

    else:

        vaccination_coverage = 0

    # --------------------------------------------------------
    # ALERTS
    # --------------------------------------------------------

    alerts = []

    for village in villages:

        if village["risk"] == "HIGH":

            alerts.append({

                "type":
                    "HIGH RISK",

                "severity":
                    "HIGH",

                "village":
                    village["village"],

                "block":
                    village["block"],

                "message": (
                    "High-risk disease activity "
                    "requires immediate veterinary "
                    "attention."
                )
            })

        elif village["active_cases"] >= 3:

            alerts.append({

                "type":
                    "WATCH",

                "severity":
                    "MODERATE",

                "village":
                    village["village"],

                "block":
                    village["block"],

                "message": (
                    "Multiple active cases have "
                    "been reported in this village."
                )
            })

    alerts = alerts[:20]

    # --------------------------------------------------------
    # RECENT CASES
    # --------------------------------------------------------

    recent_cases = []

    for report in reports[:50]:

        recent_cases.append({

            "id":
                report.get("id"),

            "village":
                report.get(
                    "village",
                    "Unknown"
                ),

            "block":
                report.get(
                    "block",
                    "Unknown"
                ),

            "animal_type":
                report.get(
                    "animal_type",
                    "Unknown"
                ),

            "risk_level":
                report.get(
                    "risk_level",
                    "LOW"
                ),

            "case_status":
                report.get(
                    "case_status",
                    "UNDER_REVIEW"
                ),

            "affected_count":
                report.get(
                    "affected_count",
                    0
                ),

            "created_at":
                report.get(
                    "created_at"
                )
        })

    # --------------------------------------------------------
    # TOTALS
    # --------------------------------------------------------

    totals = {

        "total_villages":
            len(villages),

        "total_animals":
            total_animals,

        "active_cases":
            total_active_cases,

        "high_risk_cases":
            total_high_risk,

        "high_risk_villages":
            sum(
                1
                for village in villages
                if village["risk"] == "HIGH"
            ),

        "suspected_outbreaks":
            len(outbreak_villages),

        "deaths":
            total_deaths,

        "vaccination_records":
            len(vaccinations),

        "vaccinated_animals":
            vaccinated_animals,

        "vaccination_coverage":
            vaccination_coverage,

        "blocks":
            len(blocks)
    }

    # --------------------------------------------------------
    # RENDER DISTRICT DASHBOARD
    # --------------------------------------------------------

    return render_template(
        "district_dashboard.html",
        district_name=(
            district_name
            + " District"
        ),
        totals=totals,
        blocks=blocks,
        villages=villages,
        alerts=alerts,
        recent_cases=recent_cases
    )
