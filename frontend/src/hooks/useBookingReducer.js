const initialState = {
  modal: { isOpen: false, product: null, quantity: 1 },
  form: { customer_name: "", customer_phone: "" },
  loading: false,
  success: false,
  error: null,
  orderInfo: null,
};

function bookingReducer(state, action) {
  switch (action.type) {
    case "OPEN_MODAL":
      return {
        ...state,
        modal: { isOpen: true, product: action.product, quantity: 1 },
        form: { customer_name: "", customer_phone: action.phone || "" },
        success: false,
        error: null,
        orderInfo: null,
      };
    case "CLOSE_MODAL":
      return initialState;
    case "SUBMIT_START":
      return { ...state, loading: true, error: null };
    case "SUBMIT_SUCCESS":
      return {
        ...state,
        loading: false,
        success: true,
        orderInfo: action.order,
      };
    case "SUBMIT_ERROR":
      return { ...state, loading: false, error: action.error };
    case "UPDATE_FORM":
      return {
        ...state,
        form: { ...state.form, [action.field]: action.value },
      };
    case "UPDATE_QUANTITY":
      return {
        ...state,
        modal: {
          ...state.modal,
          quantity: action.value === '' ? 1 : Math.max(1, parseInt(action.value) || 1),
        },
      };
    default:
      return state;
  }
}

export { initialState, bookingReducer };
