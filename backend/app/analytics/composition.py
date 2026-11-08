"""Provenance-preserving composition, not a physical vehicle digital twin."""
from .advanced import observed_stint_points, state_space_stints, compare_stint_models
from .bayesian import bayesian_tyre_model
from .digital_twin import integrated_scenario
from .validation import audit_session,audit_telemetry_ranges,audit_lap_set_consistency


def compose_public_data_report(laps,stints,car=None,location=None,weather=None,race_control=None,
                               scenario=None,source='OpenF1',state_mode='smooth',filter_q=None,filter_r=None):
    points=observed_stint_points(laps,stints)
    report={'ready':bool(points),'provenance':{'source':source,'observed_laps':len(laps or []),
                'observed_stints':len(stints or []),'retained_points':len(points),
                'observed_car_samples':len(car or []) if car is not None else None},
            'quality':audit_session(laps,stints,car,location,weather,race_control),
            'telemetry_sanity':audit_telemetry_ranges(car),
            'cross_source_consistency':audit_lap_set_consistency(laps,stints,car),
            'bayesian':bayesian_tyre_model(laps,stints),
            'state_space':state_space_stints(points, mode=state_mode, process_variance=filter_q, measurement_variance=filter_r),
            'chronological_benchmark':compare_stint_models(points),
            'proprietary_inputs':{key:{'status':'unavailable','reason':'Not present in public OpenF1/Jolpica feeds'} for key in
                 ('pirelli_internal_tyre_data','cfd_wind_tunnel','battery_state','ers_commands')},
            'physics_vehicle_twin':{'status':'unavailable','reason':'No calibrated vehicle dynamics/aero/energy state model'}}
    if scenario is not None:
        config=dict(scenario)
        if state_mode == 'filter' and config.get('use_bayesian_tyre_slope'):
            report['scenario']={'status':'unavailable','reason':'Causal filter mode forbids Bayesian slope estimated using all laps. Fit slope on independent past training laps first.'}
            return report
        if config.pop('use_bayesian_tyre_slope',False):
            if not report['bayesian'].get('ready'):
                report['scenario']={'status':'unavailable','reason':'Bayesian tyre fit insufficient'}
                return report
            config['tyre_slope_s']=report['bayesian']['posterior_mean_s_per_lap']
            provenance='bayesian_posterior_mean_estimate'
        else:provenance='explicit_user_assumption'
        if 'tyre_slope_s' not in config:
            report['scenario']={'status':'unavailable','reason':'Supply tyre_slope_s or use_bayesian_tyre_slope; no implicit coefficient'}
        else:
            try:
                report['scenario']=integrated_scenario(**config)
                report['scenario']['tyre_slope_provenance']=provenance
                report['scenario']['uncertainty_warning']='Tyre posterior uncertainty not propagated; scenario bands are observation-noise only.'
            except (ValueError,TypeError) as exc:
                report['scenario']={'status':'unavailable','reason':str(exc)}
    return report
