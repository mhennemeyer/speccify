require 'test_helper'

class MyModelsControllerTest < ActionController::TestCase
  test "should get index" do
    get :index
    assert_response :success
    assert_not_nil assigns(:my_models)
  end

  test "should get new" do
    get :new
    assert_response :success
  end

  test "should create my_model" do
    assert_difference('MyModel.count') do
      post :create, :my_model => { }
    end

    assert_redirected_to my_model_path(assigns(:my_model))
  end

  test "should show my_model" do
    get :show, :id => my_models(:one).id
    assert_response :success
  end

  test "should get edit" do
    get :edit, :id => my_models(:one).id
    assert_response :success
  end

  test "should update my_model" do
    put :update, :id => my_models(:one).id, :my_model => { }
    assert_redirected_to my_model_path(assigns(:my_model))
  end

  test "should destroy my_model" do
    assert_difference('MyModel.count', -1) do
      delete :destroy, :id => my_models(:one).id
    end

    assert_redirected_to my_models_path
  end
end
