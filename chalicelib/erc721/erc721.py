#!/usr/bin/env python3
import sys
import collections
from slither.slither import Slither
from slither.slithir.operations.event_call import EventCall
from slither.slithir.operations.index import Index as IndexOperation
from slither.slithir.operations.binary import Binary as BinaryOperation
from slither.slithir.operations.solidity_call import SolidityCall as SolidityCallOperation
from slither.solc_parsing.variables.state_variable import StateVariableSolc
from slither.core.solidity_types.mapping_type import MappingType
from .constants import (
    ERC721_EVENT_SIGNATURES,
    ERC721_FX_SIGNATURES,
    ERC721_ON_RECEIVE_SIGNATURES,
    ERC721_GETTERS,
    ERC721_EVENT_BY_FX,
    ALLOWANCE_FRONTRUN_FX_SIGNATURES,
    ALLOWANCE_FRONTRUN_EVENT_BY_FX,
)
from .log import (
    log_matches,
    log_event_per_function,
    log_modifiers_per_function,
    log_approve_checking_balance
)

def get_contract_from_name(slither, contract_name):
    contract = slither.get_contract_from_name(contract_name)
    return contract if type(contract) is not list else contract[0]


def is_visible(function):
    """Check if function's visibility is external or public"""
    return is_public(function) or is_external(function)


def is_external(function):
    """Check if function's visibility is external"""
    return function.visibility == "external"


def is_public(element):
    """Check if element's (Function or Event) visibility is public"""
    return element.visibility == "public"

def is_interface(contract):
    """Check if contract is interface"""
    return contract.contract_kind == "interface"


def verify_signatures(elements, expected_signatures):
    """
    Compares a list of elements (functions or events) and expected signatures.
    Returns a list of tuples containing (Signature, matching object or None)
    """
    return [(sig, sig.find_match(elements)) for sig in expected_signatures]


def verify_getters(state_variables, functions, expected_getters):
    """Checks whether getters are present either as public state variables or as visible functions."""
    for getter in expected_getters:
        # Check in state variables. If none is found, check in functions.
        if (
            any(name_and_return_match(v, getter) and is_public(v) for v in state_variables) or
            getter.find_match(functions)
        ):
            yield (getter, True)
        else:
            yield (getter, False)


def verify_event_calls(functions, events):
    """Checks if functions emit the expected events"""
    for match in functions:
        function = match[1]
        if function and events[match[0].name]:
            yield (match[0], emits_event(function, events[function.name]))


def verify_custom_modifiers(functions):
    """Checks if functions found have any modifier"""
    for match in functions:
        function = match[1]
        if function and function.modifiers:
            yield (match[0], function.modifiers)           


def name_and_return_match(variable, signature):
    """Check whether a variable's name and type match a signature."""
    return (variable.name == signature.name and
            str(variable.type) == signature.returns[0])

def get_all_functions(functions):
    """Return a list of functions"""
    return [f for f in functions]

def get_visible_functions(functions):
    """Filter functions, keeping the visible ones"""
    return [f for f in functions if is_visible(f)]


def get_implemented_functions(functions):
    """Filter functions, keeping those who are NOT declared in an interface"""
    return [f for f in functions if not is_interface(f.contract_declarer) and f.nodes]


def is_event_call(obj):
    """Return True if given object is an instance of Slither's EventCall class. False otherwise."""
    return isinstance(obj, EventCall)


def get_events(function):
    """Return a generator of events emitted by the function"""
    for node in getattr(function, 'nodes', []):
        for ir in node.irs:
            if is_event_call(ir):
                yield ir


def emits_event(function, expected_event):
    """Check whether a function (and its internal functions) emits an expected event"""
    for event in get_events(function):
        if (
            event.name == expected_event.name and 
            all(str(arg.type) == expected_event.args[i] for i, arg in enumerate(event.arguments))
        ):
            return True

    # Event is not fired in function, so check internal calls to other functions
    if any(emits_event(f, expected_event) for f in getattr(function, 'internal_calls', [])):
        return True

    # Event is not fired in function nor in internal calls
    return False


def local_var_is_sender(local_variable):
    """Check if the passed local variable's value is the msg.sender address,
    recursively checking for previous assignments."""
    
    if local_variable.name == 'msg.sender':
        return True
    else:
        try:
            # Recursively check for msg.sender assignment
            return local_var_is_sender(local_variable.expression.value)
        except AttributeError:
            return False


def checks_sender_balance_in_require(node):
    """Check if a state mapping is being accessed with msg.sender index
    inside a require statement and compared to another value, in the given node."""
    # First check we're in a require clause
    if any(call.name == 'require(bool)' for call in node.internal_calls):

        # Now check that the operations done in the node are the expected
        expected_operations = {IndexOperation, BinaryOperation, SolidityCallOperation}
        if len(node.irs) == len(expected_operations) and {type(ir) for ir in node.irs} == expected_operations:
            for ir in node.irs:
                # Verify that a state mapping is being accessed with msg.sender index
                if isinstance(ir, IndexOperation):
                    reading_mapping_in_state = (
                        isinstance(ir.variable_left, StateVariableSolc) and
                        isinstance(ir.variable_left.type, MappingType)
                    )
                    index_is_sender = local_var_is_sender(ir.variable_right)
                    if reading_mapping_in_state and index_is_sender:
                        return True                

    return False


def run(filename, contract_name):
    """Executes script"""

    # Init Slither
    slither = Slither(filename)

    # Get an instance of the contract to be analyzed
    contract = get_contract_from_name(slither, contract_name)
    if not contract:
        print("Contract {contract_name} not found")
        print("Either you mispelled the contract's name or solc cannot compile the contract.")
        exit(-1)

    # Obtain all visible functions, filtering out any that comes from an interface contract
    all_functions = get_implemented_functions(contract.functions)

    # Obtain all visible functions, filtering out any that comes from an interface contract
    visible_functions = get_visible_functions(
        get_implemented_functions(contract.functions)
    )

    erc20_fx_matches = verify_signatures(visible_functions, ERC721_FX_SIGNATURES)

    print("== ERC721 functions definition ==")
    log_matches(erc20_fx_matches)

    print("\n== Custom modifiers ==")
    log_modifiers_per_function(
        verify_custom_modifiers(erc20_fx_matches)
    )

    print("\n== ERC721 events ==")
    log_matches(
        verify_signatures(contract.events, ERC721_EVENT_SIGNATURES),
        log_return=False
    )
    log_event_per_function(
        verify_event_calls(erc20_fx_matches, ERC721_EVENT_BY_FX),
        ERC721_EVENT_BY_FX
    )

    print("\n== ERC721 getters ==")
    log_matches(
        verify_getters(
            contract.state_variables,
            visible_functions,
            ERC721_GETTERS
        )
    )

    # print("\n== Allowance frontrunning mitigation ==")
    # frontrun_fx_matches = verify_signatures(visible_functions, ALLOWANCE_FRONTRUN_FX_SIGNATURES)
    # log_matches(frontrun_fx_matches)
    # log_event_per_function(
    #     verify_event_calls(frontrun_fx_matches, ALLOWANCE_FRONTRUN_EVENT_BY_FX),
    #     ALLOWANCE_FRONTRUN_EVENT_BY_FX,
    #     must=False
    # )

    
    # print("\n== Balance check in approve function ==")
    # approve_signature = ERC721_FX_SIGNATURES[0].to_string(with_return=False, with_spaces=False)
    # approve_function = contract.get_function_from_signature(approve_signature)
    # is_checking_balance = any(checks_sender_balance_in_require(node) for node in approve_function.nodes)
    # log_approve_checking_balance(is_checking_balance)

    print("\n== Callback function")
    erc721_on_receive_matches = verify_signatures(all_functions, ERC721_ON_RECEIVE_SIGNATURES)
    log_matches(erc721_on_receive_matches)   


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print('Usage: python erc20.py <contract.sol> <contract-name>')
        exit(-1)

    FILE_NAME = sys.argv[1]
    CONTRACT_NAME = sys.argv[2]

    run(FILE_NAME, CONTRACT_NAME)
