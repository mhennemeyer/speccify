require File.dirname(__FILE__) + "/rails_test_helper.rb"

describe MyModelsController, "Functional Test", :type => ActionController::TestCase do
  it "should get index" do
     get :index
     @response.should be_success
     assigns(:my_models).should_not be_nil
   end

   describe "nested context" do
     it "should still work" do
       get :index
       @response.should be_success
       assigns(:my_models).should_not be_nil
     end
   end

   it "knows about my_models_path" do
     my_models_path.should eql("/my_models")
   end
end

